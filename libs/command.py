
import re

class Command:
    def __init__(self, pattern, help, executor):
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.executor = executor
        self.help = help
    
    def match_and_execute(self, cmdstr):
        m=re.match(self.pattern, cmdstr)        
        if m:
            args=list(m.groups())
            if len(args)>0:
                return self.executor(*args)
            else:
                return self.executor()
        else:
            return None
        
    