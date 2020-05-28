# import getpass
import os
import subprocess
import app_api
import cleanUp
import connection

number_of_api_instances=2

def main():
    ###########################################################################
    #
    # get credentials
    #
    ###########################################################################
    conn = connection.main()
    cleanUp.main(conn)

    for node in range (number_of_api_instances):
        app_api.main(conn)

    subprocess.call(['./lb.sh'])

if __name__ == '__main__':
    main()
