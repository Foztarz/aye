import numpy as np
import re

# source: http://stackoverflow.com/a/842871/5799810
def wordlist_to_regex(words):
    escaped = map(re.escape, words)
    combined = '|'.join(sorted(escaped, key=len, reverse=True))
    return re.compile(combined)

types = ['uv', 'pol-0', 'pol-45', 'pol-90', 'ir', 'vis']
hostnames = [*map(lambda type: 'aye-' + type, types)]
hostnames_pattern = wordlist_to_regex(hostnames)

pol_hostnames_pattern = wordlist_to_regex(filter(lambda a: 'pol' in a, hostnames))

def normalized_uint8(array, divider=None):
    if divider is None:
        divider = np.amax(array) 
    return np.uint8(255*array/divider)


