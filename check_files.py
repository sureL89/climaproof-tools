from cfchecker import cfchecks
import os

ls_files = os.listdir("data")

checker = cfchecks.CFChecker(silent=True)

for nc_file in ls_files:
    res = checker.checker("data/{}".format(nc_file))
    print(nc_file)
    for var in res['variables']:
        print(var)
        for err_type in ('WARN', 'ERROR', 'FATAL', 'VERSION'):
            print '\t{}: {}'.format(err_type, res['variables'][var].get(err_type, 'NOT SPECIFIED'))
    print("------------------")
