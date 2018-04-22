import time
import logging
import chat
import imp
import traceback
import json
import re
import math
import sys
import atexit
import json

from irc.bot import ServerSpec, SingleServerIRCBot
from threading import Thread
from os.path import isfile

logging.basicConfig(filename="bot.log", level=logging.DEBUG)
idata = ""
markovIn = None
retrieve = 1

if isfile("markov.bson.xz"):
    markovIn = open("markov.bson.xz", "rb")

allChain = chat.MarkovChain(order=9, filename=markovIn)
# allChain.save(open("markov.bson.xz", "wb"))

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.terminator = ""

formatter = logging.Formatter('\r%(name)-12s: %(levelname)-8s %(message)s\n$')
console.setFormatter(formatter)

logging.getLogger('').addHandler(console)
last = ""

class LonedudeBot(SingleServerIRCBot):
    def __init__(self, server, port, channels, chain = None):
        super().__init__([ServerSpec(server, port)], "Lonedude", "A simple Markov bot by Gustavo6046")
        self.chain = chain or chat.MarkovChain()
        self.joinchans = channels
        
    def on_pubmsg(self, connection, event):
        mcommand = event.arguments[0].startswith("()markov") and ( len(event.arguments[0]) == 8 or event.arguments[0].startswith("()markov ") )
        
        if mcommand or re.search(re.escape(connection.nickname) + '([,.:;]* |$)', event.arguments[0]) != None:
            data = event.arguments[0]
            
            res = None
            
            mat = re.search(re.escape(connection.nickname) + '([,.:;]* |$)', event.arguments[0])
            if mat != None and len(data) > len(mat.group(0)):
                data = data[data.find(connection.nickname) + len(re.search(re.escape(connection.nickname) + '([,.:;]* |$)', event.arguments[0]).group(0)):]
                
            elif data.startswith('()markov '):
                data = data[9:]
                
            else:
                return
                
            def _r():
                if data is not None:
                    try:
                        last = res = self.chain.get(data, 250)
                        
                    except BaseException as e:
                        for l in traceback.format_exc().split("\n"):
                            logging.error(l)
                            
                        self.connection.privmsg(event.target, "[{}: {} ({})!]".format(event.source.nick, type(e).__name__, str(e)))
                        res = False
                            
                    finally:
                        try:
                            self.chain.parse(data)
                            
                        except BaseException as e:
                            for l in traceback.format_exc().split("\n"):
                                logging.warning(l)
                        
                else:
                    try:
                        last = res = self.chain.random(250)
                        
                    except BaseException as e:
                        for l in traceback.format_exc().split("\n"):
                            logging.error(l)
                            
                        self.connection.privmsg(event.target, "[{}: {} ({})!]".format(event.source.nick, type(e).__name__, str(e)))
                        res = False
                    
                if not res:
                    self.connection.privmsg(event.target, "[{}: No Markov data!]".format(event.source.nick))
                    
                else:
                    for u in self.channels[event.target].users():
                        if res.lower().find(str(u.lower())) > -1:
                            print("Stripping nickname: {}".format(repr(u.lower())))
                            
                            res = res[:res.lower().find(str(u.lower()))] + res[res.lower().find(str(u.lower())) + len(u.lower()):]
                    
                    res = res.strip(" ")
                    self.connection.privmsg(event.target, "{}: {}".format(event.source.nick, res))
                
            global retrieve
                
            Thread(target=_r, name="#{} Markov Retriever".format(retrieve)).start()
            retrieve += 1
        
        elif event.arguments[0] in ("()like", "()up", "()good"):
            self.chain.add_score(1, last)
            self.connection.privmsg(event.target, "{}: Sentence weight increased.".format(event.source.nick))
            
        elif event.arguments[0] in ("()dislike", "()down", "()bad"):
            self.chain.add_score(-1, last)
            self.connection.privmsg(event.target, "{}: Sentence weight decreased.".format(event.source.nick))
        
        elif event.arguments[0] == "()reload":
            try:
                global chat
                
                chat = imp.reload(chat)
                self.chain = chat.MarkovChain(order=9, filename=allChain)
                allChain = self.chain
                
            except BaseException:
                for l in traceback.format_exc().split("\n"):
                    logging.error(l)
                    
                self.connection.privmsg(event.target, "[{}: Error reloading!]".format(event.source.nick))
                
            else:
                self.connection.privmsg(event.target, "[{}: Reloaded succesfully.]".format(event.source.nick))
            
        else:
            try:
                self.chain.parse(event.arguments[0])
                
            except BaseException as e:
                for l in traceback.format_exc().split("\n"):
                    logging.error(l)
        
    def on_endofmotd(self, connection, event):
        logging.debug("Joining channel")
        
        for c in self.joinchans:
            self.connection.join(c)

def _exit_bots():
    pass

if __name__ == "__main__":
    def _on_exit():
        _exit_bots()
            
        allChain.save(open("markov.bson.xz", "wb"))
        
    atexit.register(_on_exit)
    
    if len(sys.argv) > 1:
        omniChar = 0
        omniLines = 0
        
        for fi, a in enumerate(sys.argv[1:]):
            lines = list(filter(lambda x: len(x) > allChain.order, map(lambda x: x.lstrip('\n').split('\n')[0], open("./parsedata/{}.txt".format(a)).readlines())))
            allChar = sum(map(len, lines))
            omniChar += allChar
            omniLines += len(lines)
            charInd = 0
            
            for i, l in enumerate(lines):
                charInd += len(l)
                perc = str(math.floor(100 * charInd / allChar))
                rl = "\rFile {} out of {}: {}/{} ({}{}%)".format(fi + 1, len(sys.argv) - 1, i, len(lines), " " * (3 - len(perc)), perc)
                rl += " " * max(50 - len(rl), 0)
                sys.stdout.write(rl)
                allChain.parse(l)
                
        print("Parsed {} characters and {} lines.".format(omniChar, omniLines))
            
        ofp = open("markov.bson.xz", "wb")

    else:        
        conns = {}
                
        for s in json.load(open("config.json")):
            conns[s[1]] = LonedudeBot(s[0], 6667, s[2:], allChain)
            Thread(target=conns[s[1]].start, name="Bot: {}".format(s[0])).start()

        def _listenInput():
            global idata
            logging.info("*** Listening at stdin for user input now.")
            
            while True:
                c = sys.stdin.read(1)
                
                if c != '':
                    idata += c
                    logging.info(repr(idata))
                    time.sleep(0.1)
                    
                else:
                    time.sleep(0.5)
                    
        def _nexit():
            for c in conns.values():
                c.disconnect("Lonedude Markov Chain Monte Carlo Engine v0.1.0")
                
        _exit_bots = _nexit

        # Thread(target=_listenInput, name="Input Thread").start()
        
        while True:
            console.setFormatter(logging.Formatter('\r%(name)-12s: %(levelname)-8s %(message)s\n${}'.format(idata)))
            
            if idata.find('\n') < 0:
                time.sleep(0.2)
                continue

            idata = idata.split('\n')[-1]
            cmds = idata.split('\n')[:-1]
            
            for cmd in cmds:
                if ":" not in cmd:
                    cmd += ":"
                
                con = cmd.split(":")[0]
                cmd = cmd[len(con) + 1:]
                
                if con not in conns:
                    if con == "eval":
                        print(cmd, '->', eval(cmd))
                        
                    elif con == "clear":
                        allChain.data = {}
                        allChain.back = {}
                        allChain.fw_weights = {}
                        allChain.bw_weights = {}
                        allChain.save(open("markov.bson.xz", "wb"))

                    time.sleep(0.2)
                    continue
                
                if cmd != '':
                    print("* Sending to {}".format(con))
                    conns[con].connection.send_raw(cmd)
