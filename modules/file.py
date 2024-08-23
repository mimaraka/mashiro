import glob
import os
import re


def make_filename_by_seq(filepath, seq_digit=5):
    filepath_without_ext, ext = os.path.splitext(filepath)
    
    pattern = f'{filepath_without_ext}_([0-9]*){ext}'
    prog = re.compile(pattern)

    files = glob.glob(
        f'{filepath_without_ext}_[0-9]*{ext}'
    )

    max_seq = -1
    for f in files:
        m = prog.match(f)
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    
    new_filepath = f'{filepath_without_ext}_{max_seq+1:0{seq_digit}}{ext}'
    return new_filepath