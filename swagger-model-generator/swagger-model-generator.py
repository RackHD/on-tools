import string
import re
import json
import os
import sys
import yaml

dir = '.'
root_fname = ''
need_flatten = {}
definitions = {}

def flatten_ref(obj):
    for key in obj.keys():
        if key == "$ref":
            if obj[key] in need_flatten:
                #sys.stderr.write('flattening ' + obj[key] +'\n')
                refptr = need_flatten[obj[key]]
                del obj[key]
                for key2 in refptr:
                    obj[key2] = refptr[key2]
    return obj

def modify_key_ref(obj):
    for key in obj.keys():
        if key in ['longDescription', 'enumDescriptions', 'patternProperties', 'additionalProperties', 'requiredOnCreate']:
            # do not output these fields yet, unused right now
            # obj['x-'+key] = obj[key]
            del obj[key]
        if key == 'readonly':
            obj['readOnly'] = obj[key]
            del obj[key]
        if key == 'anyOf':
            # anyOf is not valid swagger, force the first option in anyOf list instead
            obj['$ref'] = obj[key][0]['$ref']
            del obj[key]
        if key == 'type':
            # swagger is deterministic and doesn't like json type lists.
            # when we see a typelist, grab the first entry and drop the null
            if not isinstance(obj[key], basestring):
                if isinstance(obj[key], list):
                    if(len(obj[key]) == 2):
                        obj[key] = obj[key][0]
        if key == "$ref":
            ref = re.sub('http://redfish.dmtf.org/schemas/v1/', '', obj[key])
            m = re.match(r"(.+)\.json#/definitions/(.+)$", ref)
            if m:
                obj[key] = '#/definitions/' + m.group(1) + '_' + m.group(2)
            else:
                m = re.match(r"#/definitions/(.+)$", ref)
                if m:
                    obj[key] = '#/definitions/' + root_fname + '_' + m.group(1)
    return obj

def load_directory(dir):
    global root_fname
    for fname in os.listdir(dir):
        if '.json' not in fname:
            continue

        root_fname = fname[:-5]
        fpath = os.path.join(dir, fname)

        sys.stderr.write('Processing ' + dir + '/' + root_fname + '...\n')

        with open(fpath, 'r') as file_handle:
            json_dict = json.load(file_handle, object_hook=modify_key_ref)
            try:
                for key in json_dict['definitions']:
                    if 'properties' not in json_dict['definitions'][key]:
                        need_flatten['#/definitions/' + root_fname +'_'+key] = json_dict['definitions'][key]
                    else:
                        definitions[root_fname+'_'+key] = json_dict['definitions'][key]
            except:
                sys.stderr.write('  Failed to process\n')

class noalias_dumper(yaml.SafeDumper):
    def ignore_aliases(self, _data):
        return True

dirs = sys.argv[1:]
for dir in dirs:
    print dir
    load_directory(dir)


with open('./definitions.yaml', 'w') as file_handle:
    output = {}
    for key in definitions:
        output[key] = json.loads(json.dumps(definitions[key]), object_hook=flatten_ref)
    
    try:
        with open('./ignore_ref.json', 'r') as ignore_refs:
            ignored = json.load(ignore_refs)
            for to_remove in ignored['ignore-ref']:
                del output[to_remove]
                print 'deleted ' + to_remove
    except:
        pass

    #json.dump(output, file_handle, sort_keys=True, indent=4, separators=(',', ': '))
    yaml_data = {}
    yaml_data['definitions'] = output
    file_handle.write( yaml.dump(yaml_data, default_flow_style=False, Dumper=noalias_dumper))
