#!/usr/bin/env python3

import argparse
from configparser import ConfigParser
import json
import os
import requests
import shutil
import subprocess
import sys
import time
import zipfile

# /* An auxilliary function that executes external command */

def exec_External_Command(cmd):
    print( F"Executing command {cmd} ." )
    msg = ""
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    (output, err) = process.communicate()
    exit_code = process.wait()
    if exit_code != 0:
        try:
            msg = err.strip()
        except:
            msg = "Generic error."
    else:
        try:
            msg = output.strip()
        except:
            msg = "Empty stdout."
    return int(exit_code), msg

# /* END exec_External_Command function BLOCK */

# /* Gets token for Gitlab asccess */

def get_Token():
    try:    
        # instantiate
        config = ConfigParser()

        # parse existing file
        config.read('/etc/rpmbuilder.ini')

        # read values from a section
        token = config.get('credentials', 'token')
    
        return token
    except:
        print("Unable to get Gitlab token")
        sys.exit(3)

# /* END BLOCK */

# /* Returns project ID of chosen repository ^/

def get_Repo_Id(gitlab_url, repo_name, gitlab_token):
    try:
        project_search_url = F"{gitlab_url}/api/v4/projects/?search={repo_name}"

        req = requests.get( project_search_url, headers = { "Private-Token" : gitlab_token } )
        if( req.status_code == 200 ):
            print("Repo information retrieved: OK.")
            return req.json()[0]['id']
        else:
            print( F"Bad answer from {gitlab_url}/api/v4/projects : {req.headers}" )
            sys.exit(6)
    except:
        print( F"Problem occured while accessing {gitlab_url}/api/v4/projects endpoint. Exiting." )
        sys.exit(4)

# /* END BLOCK */

# /* Advanced args parsing */

def parse_Args():
    parser = argparse.ArgumentParser()

    # // Obligatory parameters
    parser.add_argument( '--current_time', dest = 'current_time', action = 'store', \
                        required = True, help = 'Current UNIX timestamp' )

    parser.add_argument( '--get_src_method', dest = 'get_src_method', action = 'store', \
                        required = True, help = 'Method of getting sources. Supported options: git_clone ( native git+ssh ) and gitlab_api ( Gitlab API ). Default is gitlab_api', \
                        default = "gitlab_api")

    parser.add_argument( '--gitlab_url', dest = 'gitlab_url', action = 'store', \
                        required = True, help = 'The URL for sources downloading. Either ssh or https, depending on get_src_method.', \
                        default = "")
    
    parser.add_argument('--pkg_branch', dest = 'pkg_branch', action = 'store', \
                        required = True, help = 'Branch that should be built into package. Default is master.', default = "master" )

    parser.add_argument('--release_ver', dest = 'release_ver', action = 'store', \
                        required = True, help = 'Release version. Default is 1.', default = "1" )

    parser.add_argument('--pkg_version', dest = 'pkg_version', action = 'store', \
                        required = False, help = 'Package version. Default is UNIX timestamp.' , default = int(time.time()) ) 

    parser.add_argument('--build_container_image', dest = 'build_container_image', \
                        action = 'store', required = True, help = 'Auxiliary docker build image', default = "" )

    parser.add_argument('--repository_name', dest = 'repository_name', action = 'store', \
                        required = True, help = 'Repository name, e.g. asgardahost-rpm_repository', default = "" )

    # // Optional parameters. 
    parser.add_argument('--curl_token_file', dest = 'curl_token_file', action = 'store', \
                        required = False, help = 'File with Gitlab token for curl. Obligatory if get_src_method is gitlab_api', default = "" )

    parser.add_argument('--git_ssh_key', dest = 'git_ssh_key', action = 'store', \
                        required = False, help = 'Ssh key for access to Gitlab. Obligatory if get_src_method is git_clone', default = "" )

    parser.add_argument('--build_deps_repo', dest = 'build_deps_repo', action = 'store', \
                        required = False, help = 'File with repos containing deps for building. Obligatory if get_src_method is git_clone', default = "" )

    parser.add_argument('--spec_file', dest = 'spec_file', action = 'store', \
                        required = False, help = 'A spec file. Must be specified explicitly for git_clone method. Obligatory if get_src_method is git_clone', default = "" )

    args = parser.parse_args()

    if args.get_src_method not in ('git_clone', 'gitlab_api'):
        args.print_help()
        sys.exit(9)
    elif ( args.get_src_method == 'gitlab_api' and args.curl_token_file == "" ):
        print( "Missing config file with Gitlab token for curl. It is obligatory for geting spources via Gitlab API." )
        args.print_help()
        sys.exit(10)
    elif( args.get_src_method == 'git_clone' and ( args.git_ssh_key == "" or args.build_deps_repo == "" or args.spec_file == "" ) ):
        print( "Missing either ssh key for access to Gitlab or file with repos with build deps. It is obligatory for geting spources via native git clone command." )
        sys.exit(11)

    # //Adjustment for paramters which have to be absolute paths.

    args.curl_token_file = os.path.abspath(args.curl_token_file)
    args.git_ssh_key = os.path.abspath(args.git_ssh_key)
    args.build_deps_repo = os.path.abspath(args.build_deps_repo)
    args.spec_file = os.path.abspath(args.spec_file)

    return args

# /* END BLOCK */

# /* Download SPEC file using Gitlab API */

def get_Spec_File(gitlab_url, repo_name, project_id, branch, gitlab_token, current_time):
    try:
        spec_dl_url = F"{gitlab_url}/api/v4/projects/{project_id}/repository/files/SPEC%2F{repo_name}%2Espec/raw?ref={branch}"

        req = requests.get( spec_dl_url, headers = { "Private-Token" : gitlab_token } )
        print(req.status_code)
        if( req.status_code == 200 ):
            print("Downloading SPEC file... Ok.")
            with open(F"{repo_name}-{branch}-{current_time}/{repo_name}.spec", 'wb') as fd:
                for chunk in req.iter_content(chunk_size=1024):
                    fd.write(chunk)
            fd.close()
        else:
            print(F"Could not download SPEC {repo_name}.spec")
            sys.exit(7)

    except:
        print( F"Problem occured while accessing {gitlab_url}/api/v4/projects endpoint. Exiting." )
        sys.exit(5)

# /* END BLOCK */

def get_Build_Deps_Repo_File(gitlab_url, repo_name, project_id, branch, gitlab_token, current_time):
    try:
        repo_dl_url = F"{gitlab_url}/api/v4/projects/{project_id}/repository/files/BUILD_DEPS_REPO%2Fbuild-deps%2Erepo/raw?ref={branch}"

        req = requests.get( repo_dl_url, headers = { "Private-Token" : gitlab_token } )
        print(req.status_code)
        if( req.status_code == 200 ):
            print("Downloading repo file for building deps... Ok.")
            with open(F"{repo_name}-{branch}-{current_time}/build-deps.repo", 'wb') as fd:
                for chunk in req.iter_content(chunk_size=1024):
                    fd.write(chunk)
            fd.close()
        else:
            print(F"Could not download SPEC {repo_name}.spec")
            sys.exit(7)

    except:
        print( F"Problem occured while accessing {gitlab_url}/api/v4/projects endpoint. Exiting." )
        sys.exit(5)

# /* END BLOCK */


# /* Download sources using Gitlab API */

def get_Sources(gitlab_url, repo_name, project_id, branch, gitlab_token, current_time ):
    try:
        archive_dl_url = F"{gitlab_url}/api/v4/projects/{project_id}/repository/archive.zip?sha={branch}"

        req = requests.get( archive_dl_url, headers = { "Private-Token" : gitlab_token } )
        print(req.status_code)
        if( req.status_code == 200 ):
            print("Downloading archive... Ok.")
            with open(F"{repo_name}-{branch}-{current_time}.zip", 'wb') as fd:
                for chunk in req.iter_content(chunk_size=1024):
                    fd.write(chunk)
            fd.close()
        else:
            print(F"Could not download archive {repo_name}.zip")
            sys.exit(7)

    except:
        print( F"Problem occured while accessing {gitlab_url}/api/v4/projects endpoint. Exiting." )
        sys.exit(5)

    try:
        with zipfile.ZipFile(F"{repo_name}-{branch}-{current_time}.zip","r") as zip_ref:
            name = zip_ref.infolist()[0].filename.strip('/')
            zip_ref.extractall(".")
    
        os.remove(F"{repo_name}-{branch}-{current_time}.zip")
        shutil.move( name, F"{repo_name}-{branch}-{current_time}/{repo_name}" )

    except:
        print( F"Failed to extract downloaded archive: {repo_name}-{branch}-{current_time}.zip" )
        sys.exit(10)

# /* END BLOCK */

def main():

    args = parse_Args( ) # // Advanced check of parsed arguments passed to the script.

    current_time = args.current_time

    # // Let's rock in our build dir 
    try:
        # instantiate
        c = ConfigParser()

        # parse existing file
        c.read('/etc/rpmbuilder.ini')

        # read values from a section
        ROOTDIR = c.get('general', 'rootdir')
    except:
        print("Unable to get rootdir")
        sys.exit(5)

    os.chdir(ROOTDIR)

    print( F"We are starting with the followings args: {args.get_src_method} | {args.gitlab_url} | {args.repository_name} \
           | {args.build_container_image} | {args.pkg_branch} | {args.pkg_version} " )

    retcode = -1
    log = ""

    if ( args.get_src_method == "git_clone" ):
        # // Preparing work directory for builder image and get spec file into it
        os.makedirs(F"{args.repository_name}-{args.pkg_branch}-{current_time}/rpmbuild/SOURCES")
        # // Run building
        print("Starting to build package. Please be patient.\n======")
        retcode, log = exec_External_Command( [ "docker", "run", "-i", "--name", F"{args.repository_name}-{args.pkg_branch}-{current_time}", "--user", "991:988",  "--mount", \
                                              F"type=bind,source={args.git_ssh_key},target=/home/rpmbuilder/rpmbuilder.rsa", "--mount", \
                                              F"type=bind,source={args.spec_file},target=/home/rpmbuilder/{args.repository_name}.spec", "--mount", \
                                              F"type=bind,source={args.build_deps_repo},target=/etc/yum.repos.d/build-deps.repo", "-v", \
                                              F"{ROOTDIR}/{args.repository_name}-{args.pkg_branch}-{current_time}:/home/rpmbuilder/work", \
                                              F"{args.build_container_image}", F"{args.gitlab_url}", F"{args.pkg_branch}", \
                                              F"{args.pkg_version}", F"{args.get_src_method}", F"{args.repository_name}.spec", F"{args.release_ver}" ] )
     
    elif ( args.get_src_method == "gitlab_api" ):

        # // Get token from configuration file
        gitlab_token = get_Token()

        # // Get project ID from specified Gitlab repository
        project_id = get_Repo_Id(args.gitlab_url, args.repository_name, gitlab_token)

        # // Preparing work directory for builder image and get spec file into it
        os.makedirs(F"{args.repository_name}-{args.pkg_branch}-{current_time}/rpmbuild/SOURCES")
        
        get_Spec_File(args.gitlab_url, args.repository_name, project_id, args.pkg_branch, gitlab_token, current_time)
        get_Build_Deps_Repo_File(args.gitlab_url, args.repository_name, project_id, args.pkg_branch, gitlab_token, current_time)
        get_Sources(args.gitlab_url, args.repository_name, project_id, args.pkg_branch, gitlab_token, current_time)

        # // Run building
        print("Starting to build package. Please be patient.\n======")
        retcode, log = exec_External_Command( [ "docker", "run", "-i", "--name", F"{args.repository_name}-{args.pkg_branch}-{current_time}", "--user", "991:988", "--mount", \
                            F"type=bind,source={args.curl_token_file},target=/home/rpmbuilder/gitlab_config.txt", "--mount", \
                            F"type=bind,source={ROOTDIR}/{args.repository_name}-{args.pkg_branch}-{current_time}/build-deps.repo,target=/etc/yum.repos.d/build-deps.repo", "-v", \
                            F"{ROOTDIR}/{args.repository_name}-{args.pkg_branch}-{current_time}:/home/rpmbuilder/work", \
                            F"{args.build_container_image}", F"{args.gitlab_url}/api/v4/projects/{project_id}/repository", F"{args.pkg_branch}", \
                            F"{args.pkg_version}", F"{args.get_src_method}", F"{args.repository_name}.spec", F"{args.release_ver}" ] )
    
    print( F"Build command finished with retcode {retcode} and message {log}\n" )
    print( "=====Successful exiting" )
    print( F"The build directory is: {ROOTDIR}/{args.repository_name}-{args.pkg_branch}-{current_time}" )

    sys.exit(0)

if __name__ == '__main__':
    main()

