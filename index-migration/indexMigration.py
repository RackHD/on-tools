import subprocess

def backup_db():
    """
    To backup mongo databases and save it to a directory called dump.bak
    """
    try:
        subprocess.check_output(['ls dump'], shell=True);
        subprocess.check_call(['rm -rf dump*'], shell=True)
    except CalledProcessError:
        pass
    subprocess.check_call(['mongodump'])
    subprocess.check_call(['cp', '-rf', 'dump', 'dump.bak'])
    subprocess.check_output(['ls dump.bak'], shell=True);

def get_collection():
    """
    To get collection names of mongo databases
    """
    label1=subprocess.Popen(['mongo', 'pxe', '--eval', 'db.getCollectionNames()'], stdout=subprocess.PIPE)
    collection_info =  label1.stdout.read().split('\n')
    collection_names= collection_info[-2].split(',')
    return collection_names

def drop_indexes():
    """
    To delete all indexes
    """
    collections=get_collection()
    errors = ['error', 'Error', 'ERROR']
    for collection in collections:
       drop_index_result = subprocess.Popen(['mongo', 'pxe', '--eval', 'db.'+collection+'.dropIndexes()'], stdout=subprocess.PIPE)
       drop_index_output =  drop_index_result.stdout.read()
       for error in errors:
          assert error not in drop_index_output, "Error is found when dropping mongo database indexes from collection %s" % collection

def main():
    """
    To execute the index migration
    """
    print "Warning! Execute this script will drop all indexes from mongo databases!\nYet the script will help you backup all mongo databases\
in a directory called dump.save under your working directory.\nIf you were to restore your mongoDB after executing this script, \
simpleyly run 'mongorestore dump.bak'.\nContinue running the script(Yes|No)?"
    for attemp in range(3):
        user_input = raw_input()
        if user_input not in ['Yes', 'No']:
            print "Incorrect input, please input Yes or No"
            if attemp == 2:  print "You've wasted 3 attempts to give a correct input, please re-run the script!"
        elif user_input == "No":
            print "The script is NOT executed!"
            break
        else:
            backup_db()
            drop_indexes()
            print "The indexes are dropped successfully!"
            break

if __name__ == '__main__':
    main()
