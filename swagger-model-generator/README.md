`swagger-model-generator` parses directories of JSON Schema files and produces a model definition in yaml
that is suitable for inclusion in a full swagger definition.

## Configuration

`pip install -r requirements.txt` will install the necessary Python dependencies.

## Usage

`python swagger-model-generator.py dir1 dir2` will probe the directories dir1 and dir2 for json 
schema files and convert their contents to a model definition output as 'definition.yaml'

The optional file `ignore_ref.json` can be used to tell the generator to prune model definitions
from the 'definition.yaml' file
