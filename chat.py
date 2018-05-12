import random
import msgpack
import logging
import traceback
import time
import math

from os.path import isfile


CHAT_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789-_.,?!@:;=+-'\"()[]{}#/\\ "

log = 0

def alphafilter(c):
    return c.lower() in CHAT_ALPHABET

def weighted_random(l):
    if not isinstance(l, list):
        return None
    
    tot = sum(map(lambda x: x[1], l), 0)
    
    if tot == 0:
        return None
    
    r = random.uniform(0, tot)
    t = .0
    
    for d in l:
        t += d[1]
        
        if r < t:
            return d[0]
        
    print(r, t)
        
    return None # something weird happened!

class MarkovChain(object):
    def __init__(self, order=3, filename=None):
        self.order = order
        
        try:
            if filename is not None:
                if isinstance(filename, MarkovChain):
                    self.data = filename.data
                    self.back = filename.back
                    
                    self.fw_weights = filename.fw_weights
                    self.bw_weights = filename.bw_weights
                    
                else:
                    if isinstance(filename, str):
                        if not isfile(filename):
                            raise RuntimeError('Markov file {} does not exist!'.format(filename))
                            
                        d = open(filename, 'rb').read()
                        
                    else:
                        d.seek(0)
                        d = filename.read()
                        
                    stuff = msgpack.unpackb(d, raw=False)
                    
                    # print(tuple(stuff.keys()), tuple(map(len, stuff.values())))
                    
                    self.data = stuff["forward"]
                    self.back = stuff["backward"]
                    
                    [self.fw_weights, self.bw_weights] = stuff["weights"]
                    
                    # print(len(self.data), len(self.back))
                
            else:
                self.data = {}
                self.fw_weights = {}
                self.bw_weights = {}
                self.back = {}
                
        except BaseException as e:
            traceback.print_exc()
            # print(type(e), e)
            
            for l in traceback.format_exc().split("\n"):
                logging.warning(l)
                
            self.data = {}
            self.back = {}
            self.weights = {}
            
            self.fw_weights = {}
            self.bw_weights = {}
            
            logging.warning("A problem occurred trying to load Markov nodes. Emptying Markov chain.")
            
        logging.debug(" ")
        logging.debug("******")
        logging.info("Loaded {} forward and {} backward Markov nodes.".format(len(self.data), len(self.back)))
        logging.debug("******")
        logging.debug(" ")
        
    def save(self, io):
        msgpack.pack({"forward": self.data, "backward": self.back, "weights": [self.fw_weights, self.bw_weights]}, io, use_bin_type=True)
        
        logging.info("Saved {} forward and {} backward Markov nodes into the Markov database.".format(len(self.data), len(self.back)))
        
    def parse(self, data):
        data = ''.join(list(filter(alphafilter, data)))
        
        numcons = len(data) - self.order
        
        if numcons < 1:
            return False
        
        cons = [[data[i:min(i + self.order, len(data) - 1)], data[min(i + self.order, len(data) - 1)]] for i in range(0, numcons)]
        
        for c in cons:
            self.add_entry(c[0], c[1].lower(), c[1])
            
        data = data[::-1]
        bcons = [[data[i:min(i + self.order, len(data) - 1)], data[min(i + self.order, len(data) - 1)]] for i in range(0, numcons)]
        
        for bc in bcons:
            self.add_entry(bc[0], bc[1].lower(), bc[1], True)
            
        return True
        
    def add_score(self, score, data):
        numcons = len(data) - self.order
        
        if numcons < 1:
            return False
        
        fcons = [[data[i:min(i + self.order, len(data) - 1)], data[min(i + self.order, len(data) - 1)]] for i in range(0, numcons)]
        bcons = [[data[i:min(i + self.order, len(data) - 1)], data[min(i + self.order, len(data) - 1)]] for i in range(0, numcons)]
        
        dfe = [b + a for [b, a] in fcons]
        dbe = [b + a for [b, a] in bcons]
        
        for d in dfe:
            self.fw_weights[d] = (self.fw_weights[d] or 0) + score
            
        for d in dbe:
            self.bw_weights[d] = (self.bw_weights[d] or 0) + score
        
    def _find(self, key, partial=True):
        key = ''.join(list(filter(alphafilter, key.lower())))
        
        if key in self.data:
            return key
            
        if partial: # slow
            for k in self.data.keys():
                if k[-len(key):] == key:
                    return k
                
        return None
    
    def _find_back(self, key, partial=True):
        key = ''.join(list(filter(alphafilter, key.lower())))
        
        if key in self.back:
            return key
            
        if partial:
            for k in self.back.keys():
                if k[-len(key):] == key:
                    return k
            
        return None
        
    def add_entry(self, key, value, case_value, back=False):
        global log
        
        if value[0] not in CHAT_ALPHABET:
            return False
        
        if log:
            print("Adding entry: '{}' -> '{}'".format(key, case_value))
            log -= 1
        
        key = ''.join(list(filter(alphafilter, key.lower())))[-self.order:]
            
        value = value[0]
        
        if ( self._find_back(key, False) is None and back ) or ( self._find(key, False) is None and not back ):
            if back:
                self.back[key] = [[[value, case_value], 1, time.time()]]
                self.bw_weights[value + key] = 0
                
            else:
                self.data[key] = [[[value, case_value], 1, time.time()]]
                self.fw_weights[value + key] = 0
        
        else:
            if back:
                key = self._find_back(key, False)
                
                for i, d in enumerate(self.back[key]):
                    if d[0] == value:
                        self.back[key][i][2] = ((self.back[key][i][2] * self.back[key][i][1]) + time.time()) / (self.back[key][i][1] + 1)
                        self.back[key][i][1] += 1
                        return
                    
                self.back[key].append([[value, case_value], 1, time.time()])
                
            else:
                key = self._find(key, False)
                
                for i, d in enumerate(self.data[key]):
                    if d[0] == value:
                        self.data[key][i][2] = ((self.data[key][i][2] * self.data[key][i][1]) + time.time()) / (self.data[key][i][1] + 1)
                        self.data[key][i][1] += 1
                        return
                            
                self.data[key].append([[value, case_value], 1, time.time()])

    def random(self, maxLen=80):
        if len(self.data.keys()) < 1:
            return None
        
        return self.get(data=random.choice(list(self.data.keys())), maxLen=maxLen)

    def get(self, data, maxLen=80):
        global log
        
        data = ''.join(list(filter(alphafilter, data)))
        
        key = data.lower()[-self.order:]
        bkey = data.lower()[:self.order][::-1]
        
        if len(key) > maxLen - 1:
            return key[:maxLen]
        
        res = ""
        cres = ""
        ndata = ''.join(list(filter(alphafilter, data.lower())))
        
        if self._find_back(key[::-1]) is None and self._find(key) is None:
            return None
        
        if self._find_back(key[::-1]) is not None:
            while len(res) < math.floor(maxLen / 2):
                if self._find_back(bkey) is None or self._find_back(bkey) not in self.back or self._find_back(bkey) is None:
                    # print(bkey, '-', ', '.join(self.back.keys()))
                    break
                
                # else:
                #     print(bkey, '+')
                
                nc = weighted_random(list(map((lambda x: [x[0], (x[1] + self.bw_weights.get(x[0][0] + self._find_back(bkey), 0)) / (time.time() - x[2]) ** 0.25]), self.back[self._find_back(bkey)]))) or ['', '']
                
                res = nc[0] + res
                cres = nc[1] + cres
                
                bkey = (res + ndata)[:self.order][::-1]

        res += ndata
        cres += ndata
        key = res[-self.order:]
        
        if self._find(key) is None:
            return cres
        
        while len(res) < maxLen:
            if self._find(key) is None:
                return cres
            
            nc = weighted_random(list(map(lambda x: [x[0], (x[1] + self.fw_weights.get(x[0][0] + self._find(key), 0)) * 10000 / (time.time() - x[2])], self.data[self._find(key)]))) or ['', '']
            
            res += nc[0]
            cres += nc[1]
            
            # print("({} -> {}) {}".format(key, nc, ares))
            
            key = res[-self.order:]
                
        return cres
