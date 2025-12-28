#!/usr/bin/env python3
import os
import sys
import shutil
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)
from vat.utils.fs_access import FolderAccessManager, FolderAccessError

def main():
    tmp = os.path.join(root, 'build', 'smoke_fs_tmp')
    # Clean and prepare temp directory
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp, exist_ok=True)
    # Create dummy files
    open(os.path.join(tmp, 'test1.mpg'), 'a').close()
    open(os.path.join(tmp, 'test2.mpg'), 'a').close()
    open(os.path.join(tmp, 'test1.wav'), 'a').close()
    open(os.path.join(tmp, 'test2.wav'), 'a').close()

    fs = FolderAccessManager()
    assert fs.set_folder(tmp), 'Failed to set folder'

    videos = fs.list_videos()
    print(f'Videos: {len(videos)} -> {[os.path.basename(v) for v in videos]}')

    wavs = fs.recordings_in()
    print(f'WAVs: {len(wavs)} -> {[os.path.basename(w) for w in wavs]}')

    # Metadata round-trip
    default = 'name: \n'
    content = fs.ensure_and_read_metadata(tmp, default)
    assert 'name:' in content
    fs.write_metadata('name: smoke\n')
    reread = fs.ensure_and_read_metadata(tmp, default)
    assert 'smoke' in reread
    print('Metadata OK')

    print('Smoke FS test completed successfully.')

if __name__ == '__main__':
    try:
        main()
    except FolderAccessError as e:
        print(f'Folder access error: {e}')
        sys.exit(1)
    except AssertionError as e:
        print(f'Assertion failed: {e}')
        sys.exit(2)
    except Exception as e:
        print(f'Unexpected error: {e}')
        sys.exit(3)
