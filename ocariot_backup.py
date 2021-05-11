#!/usr/bin/python3

import os, sys
import json

from packages import OCARIOT_REST_API


# Backup files
dir_path = os.path.dirname(os.path.realpath(__file__))
failed_filename = os.path.join(dir_path, 'backup', 'failed_posts.txt')
invalid_filename = os.path.join(dir_path, 'backup', 'invalid_posts.txt')



# def backup_successful(post):
#     create_dirs(successful_filename)
#     with open(successful_filename, "a") as backup_file:
#         json.dump(post, backup_file)
#         backup_file.write(os.linesep)



def backup_failed(post):
    create_dirs(failed_filename)
    with open(failed_filename, "a") as backup_file:
        json.dump(post, backup_file)
        backup_file.write(os.linesep)



# def backup_invalid(post):
#     create_dirs(invalid_filename)
#     with open(invalid_filename, "a") as backup_file:
#         json.dump(post, backup_file)
#         backup_file.write(os.linesep)



def create_dirs(path):
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise



def upload_failed_posts(ocariot_url):
    # Read failed posts backup file

    failed_uploads = []
    try:
        with open(failed_filename, "r+") as f:
            failed_posts = [json.loads(line) for line in f]
    except:
        return -2

    # Try to upload each failed post
    for post in failed_posts:
        type = post['type']

        if type == 1:
            child_username = post['child_number']
        elif type == 2:
            tag_uid = post['tag_uid']

        weight = post['weight']
        timestamp = post['timestamp']

        try:
            # Post child weight
            if type == 1:
                res = OCARIOT_REST_API.post_weight(ocariot_url, child_username, weight, timestamp)
            elif type == 2:
                res = OCARIOT_REST_API.post_weight_nfc(ocariot_url, tag_uid, weight, timestamp)

            if res == 409:
                print('Value already inserted!')
                print(post)
                print()


            else:
                print("Success!")
                print(res)
                print()

        except:
            print('Failed to post Child weight!')
            print(post)
            print()
            failed_uploads.append(post)



    # else:
    #     # Delete failed posts file if the for reaches the end
    os.remove(failed_filename)


    #f.writelines('\n'.join(failed_uploads))
    return 0



# ----------------- MAIN -----------------
def main():
    ocariot_url = "https://api.ocariot.lst.tfo.upm.es"
    upload_failed_posts(ocariot_url)



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nShutdown requested! Exiting...')
        sys.exit(0)
    except Exception:
        print('\nAn error occurred! Exiting...\n')
        import traceback
        traceback.print_exc()
        sys.exit(1)