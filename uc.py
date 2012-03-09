# coding=utf-8
import re
import sys
import os 
import codecs

DICT='dict/words'

#Don't split punctuation.
APOSTROPHES = u"’'"

'''
This pattern will separate contiguous sequences of alphanumeric
characters. Sequences are split not only on spaces but also on special
characters such as "{}'();. Practically what this means is that
punctuation is stripped off and the words are successfully extracted.

There are two exceptions.

The ' character is special because it can be both a quotation mark and
a quote character. We want to strip off quotation characters so we
don't parse out words with quote symbols attached, but at the same
time words can end on ' such as "sus' cabbages" or "didn't".  This
gives us certain ambiguities e.g 'the mad hatter's name was sus' sus'
was an mad man'.  Without knowledge of the english language difficult
to determine where quotes end and apostrophes begin.

This pattern will allow me to not split on whatever is defined as
apostrophes if the word has alphanumeric characters trailing after the
apostrophe. It allows me to extract words that end in an apostrophe
by removing the trailing apostrophe and for words such as "didn't"
I can keep the apostrophe.

Hyphenated words are also captured. A hyphen does not split words up.
This is so phrases such as "co-dependent", "anti-crime", or line split
words such as "amer-
ican" can be processed. 
'''

WORD_PAT = re.compile(
u"""
\w+-\w+(?:-\w+)*(?:[%s]\w+)?| #capture hypenated words. May include apostrophe.
\w+[%s]?\w+| #capture words of form word then apostrophe then word
\w #capture a single letter
""" % (APOSTROPHES,APOSTROPHES),
re.UNICODE | re.VERBOSE)

def processHyphenatedToken(ht,firstIdx,wordlist):
  '''Process hyphenated tokens. Return true if the token is recognized.

  Hyphenated tokens come in four cases:

  1) When there are two or more tokens separated by hypens then 
  the hyphenated token represents a conglomeration of words or letters.
  An example would be a-b-c's or anti-flaming-axe-league.

  When there is only one hyphen...
  2) It may be a word followed by a suffix or a prefixed word.
  An example would be co-dependent. 
  3) It may be that the hypen is used as a line break for page formatting.
  An example would be he-dge where 'he-' were the last three characters on
  a line, followed by 'dge' on the next line.
  4) It may be that it is two words or characters separated by a hypen.
  This is similar to case 1). An example: Pro-Keyboardist.

  The hyphenated token is recognized if it each hyphen separated token 
  can be found in a dictionary, the hyphenated token can be found in a 
  dictionary, or on removal of a hyphen in a single hyphenated token the
  result yields a word found in a dictionary.
  '''

  hidx = ht.find('-',firstIdx+1) #check for more than one token.
  
  #Case 1)	
  if hidx != -1:
    for token in ht.split('-'):
      if not word_in_dictionary(token,wordlist): return False
    return True
   
  if word_in_dictionary(ht,wordlist): return True #Case 2)  
  if word_in_dictionary(ht.replace('-',''),wordlist): return True #Case 3)
  for token in ht.split('-'): #Case 4)
      if not word_in_dictionary(token,wordlist): return False
  return True   

def regex_word_search_help(text):
  '''Extract words and the their positions out of the input text.
  return a list of the extracted words and a list of their positions'''

  match = None
  match = WORD_PAT.search(text)
  if not match: return []
  
  result_set = [match.group(0)]
  matchidx = [(match.start(),match.end())]
  while match:
    match = WORD_PAT.search(text,match.end())
    if match:
        matchidx.append( (match.start(),match.end()) )
        result_set.append(match.group(0))
  return result_set,matchidx

def regex_word_search(text):
  '''Maintain old name for compatibility with test cases'''
  result_set,matchidx = regex_word_search_help(text)
  return normalize_text(result_set, matchidx, text)[0]

def regex_word_search_idx(text):
  result_set,matchidx = regex_word_search_help(text)
  return normalize_text(result_set, matchidx, text)

def count_newline(seperation):
  '''Return the number of new lines in string "seperation".
  It is assumed that only a single type of new line is present.
  I.e windows new lines or linux new lines.'''
  return max(seperation.count('\n'),
             seperation.count('\r\n'),
             seperation.count('\n\r'),
             seperation.count('\r'))

def adjacent_connector(word):
  '''Sometimes adjacent capitalized words will be connected with a word that
  is not capitialized. For instance, "If You Are the One" is a television
  show from China. "the" is not capitalized but the entire name should still
  be treated as a "word". Return True if the word under examination counts as
  one of these words.'''

  connector_words = ["the","a","of"]
  if word in connector_words: return True
  return False

def cancel_non_adjacent_link(new_set, new_matchidx, connectors, lastword, lastidx):

  '''During normalization adjacent capitalized words are transformed
into single "words".  Adjacent capitalized words that are seperated by
non capitalized connector words (see adjacent_connector()) are also
transformed into single "words". If however, while parsing, it happens
that two adjacent capitalized words cannot be connected then this
function is called and the connection process is cancelled. What this
means practically is that any previous words that were in limbo,
waiting to be reduced into a single word, are instead added
individually to the list of seen words.'''

  #Add the last seen capitalized word. It won't be concatenated with any further
  #input.
  new_set.append(lastword) 
  new_matchidx.append(lastidx)
  
  #each connector word is added too since they never got a chance to link
  #capitalized words.
  for w,idx in connectors:
    new_set.append(w)
    new_matchidx.append(idx)
  del(connectors[0:])

def normalize_text(result_set, matchidx, text):
    '''Run text normalization on extracted words from text.
    this text normalization turns adjacent capitalized words
    as single words, replaces known unicode apostropheses with
    ascii ones. Returns list of normalized words as well as their
    positions in input text. Retval is a tuple.'''    
    
    #Normalize text here.
    #p.s it might be useful to take a look at the unicodedata module,
    #specifically the normalize() function.
    
    #create a new set but with adjacent upper case words treated as a single
    #word. So "new york" while in the original set is represented as two words
    #new and york, this transform the two into a single word "new york".
    #also take into account adjacent upper case words that may be connected
    #by non capitalized words such as "United States of America" 

    lastword = None # last capitalized word seen
    lastidx = None # index of last capitalized word seen
    new_set = [] #result set of words after normalization
    new_matchidx = [] #index of these words
    connectors = [] # buffer for holding connecting words: see adjacent_connector()

    for word,matchidx in zip(result_set,matchidx):
      if word[0].isupper():
        if lastword and connectors:
          con,idx = connectors[len(connectors)-1]
          seperation = text[idx[1]:matchidx[0]]

          if not seperation.isspace():
            cancel_non_adjacent_link(new_set, new_matchidx, 
                                     connectors, lastword, lastidx)
            lastword = word
            lastidx = matchidx

          else:
            connectors.append( (word,matchidx) )
            for w,idx in connectors:
              sep = text[lastidx[1]:idx[0]]
              lastword = lastword + sep + w
              lastidx = lastidx[0],idx[1]
            connectors = []
            
        elif lastword:
          seperation = text[lastidx[1]:matchidx[0]]
          
          #If the line count is greater than two then we may be dealing with
          #a quotation instead of two adjacent captialized words separated by
          #line breaks.
          #e.g
          #"So sayeth I" - Historial Figure
          #
          #This was the historial quotation of note by...
          #
          #v.s 
          #
          #If you ever happen to be in New
          #York for the chirstmas, it is very beautiful.
          #
          #Without the seperation count of 2, the first example will yield
          #a word "Historial Figure\n\nThis". In the second example
          #The word "New York" is still captured. This doesn't prevent
          #"Historial Figure\nThis" from being captured if it was only a
          #single line separation however...

          if seperation.isspace() and count_newline(seperation) < 2:
            lastword = lastword + seperation + word
            lastidx = lastidx[0],matchidx[1]
          else: 
            new_set.append(lastword)
            new_matchidx.append(lastidx)
            lastword = word
            lastidx = matchidx
        else: 
          lastword = word
          lastidx = matchidx
      
      #case Found previous capitalized word and zero or more previous connectors
      elif lastword and adjacent_connector(word): 

        #only white space is allowed between the Capitalized words,
        #their connectors, and connectors and connectors.
        if not connectors: 
          seperation = text[lastidx[1]:matchidx[0]]
        else:
          con,idx = connectors[len(connectors)-1]
          seperation = text[idx[1]:matchidx[0]]

        connectors.append( (word,matchidx) )
        if not seperation.isspace():
          #Looking at something like "Cake, and" or "Cake and, the" so add all
          cancel_non_adjacent_link(new_set, new_matchidx, 
                                   connectors, lastword, lastidx)
          lastword = None

      else:
        if lastword:
          cancel_non_adjacent_link(new_set, new_matchidx, 
                                   connectors, lastword, lastidx)
          lastword = None
        
        new_set.append(word)
        new_matchidx.append(matchidx)
    if lastword: 
      #This function is also called here to add lastword if it exists.
      #i.e it is called when no cancellation occurs in this case.
      cancel_non_adjacent_link(new_set, new_matchidx, 
                               connectors, lastword, lastidx)
    result_set = new_set

    #strip off "'s" from words.
    temp1 = [] 
    temp2 = []
    for word,idx in zip(result_set,new_matchidx):
      if re.match('[%s]s' % APOSTROPHES, word[-2:]):
          word =  word[:-2]
          temp2.append((idx[0],idx[1]-2))
      else:
        temp2.append(idx)
      pat = "[%s]" % APOSTROPHES
      word = re.sub(pat,"'", word)
      temp1.append(word)
    return temp1,temp2
        
def load_words(dict):
    '''Load a dictionary at location "dict.
    Return the result as a frozen set of words.'''
    dictfobj = codecs.open(dict, encoding="iso8859")

    #When unicode strings are compared with regular strings
    #the regular strings are converted into unicode automatically
    #(ascii is the assumed encoding)
    def tolower_and_strip(string):
        return string.lower().strip()

    words = map(tolower_and_strip, dictfobj.readlines())
    dictfobj.close()
    return frozenset(words)
    
def word_in_dictionary(word, dict): 
    try:
        if word in dict: return True
        return False
    except UnicodeWarning:
        print "WARNING: " + word


def printoutput_and_colorize(dict,text,isHTML):
  '''Output input text but with unrecognized words highlighted.  Console or HTML.

  There is a bug that sometimes highlights the empty space at the end
  of an output line. I do not know what causes this. Even creating a
  text file and placing the escape color codes in by hand will cause
  this same error. I tried viewing a manually created file with
  konsole, gnome terminal and xterm which all replicated the
  problem. The width of the window also seems to play a role in
  termining whether this bug shows up. I viewed the file by catting it.
  
  Viewing the output of this program with 'less -R' works properly though
  so it is probably a bug somewhere in whatever display mechanism konsole,
  gnome terminal and xterm share.
  
  '''

  words,idxs = regex_word_search_idx(text)
  unknown_word_idx = []
  unknown_word_set = set()
  for word,idx in zip(words,idxs):
        if word.isdigit(): continue #skip digits

        hidx = word.find('-')
        if hidx == -1 :
            if not word_in_dictionary(word.lower(),dict):
              unknown_word_idx.append(idx)
              unknown_word_set.add(word)
        elif not processHyphenatedToken(word.lower(),hidx,dict):
          unknown_word_idx.append(idx)
          unknown_word_set.add(word)

  #Highlight unknown words 

  if isHTML:
    delim_begin = '<span class="unknownword">'
    delim_end = '</span>'
  else:
    #See more ANSI color codes here: 
    #http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html
    delim_begin = "\x1b[42m"
    delim_end = "\x1b[0m"


  '''Force output to be in utf-8. On certain systems, including mine
  the default encoding reported by 'sys.getdefaultencoding()' is ascii.
  What this means is that if you redirect the output of this program
  into a file it will attempt to first convert the output into ascii and
  will crash. Instead, create byte strings and save these. 
  See: http://bugs.python.org/issue4947 for a possible relation?'''

  buf = []
  def output(offset,uwidx_iter):
    try: start,end = uwidx_iter.next()
    except StopIteration: 
      buf.append(text[offset:].encode('utf-8'))
      return
    buf.append(text[offset:start].encode('utf-8'))
    buf.append(delim_begin)
    buf.append(text[start:end].encode('utf-8'))
    buf.append(delim_end)
    output(end,uwidx_iter)

  output(0,iter(unknown_word_idx))

  stat = 'Unrecognized unique words / unique Words (%d/%d): Percent %f' 
  word_set = set(words)
  percentage = (float(len(unknown_word_set)) / len(word_set)) * 100

  stat = stat % (len(unknown_word_set),len(word_set), percentage)

  if isHTML:
    return generate_html() % (stat,''.join(buf))
  else:
    buf.append(os.linesep)
    buf.append(stat)
    return ''.join(buf)

def generate_html():
  '''Generate html output'''
  return '''
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    
    <style type="text/css">
      pre { 
        margin: auto;
        width:80em; /*width is 80 chars*/
        padding: 10px;
        border-width: thin;
        border-style: solid;
        border-color: black;
      }
      #stat { 
        margin-top:10px;
        margin-bottom:10px;
        text-align:center;
      }
      #doc {
        white-space: pre-wrap;
        overflow:hidden;
      }
      .unknownword {
        background: #ffff00;
      }
    </style>

    <link type="text/css" href="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.16/themes/start/jquery-ui.css" rel="stylesheet"/> 
    <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>
    <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.16/jquery-ui.min.js"></script>
    <script type="text/javascript">
      $(function(){
        $("#doc").resizable({animate:true});
      });
    </script>

  </head>
  <body>
    <pre id="stat">%s</pre>
    <pre id="doc">%s</pre>
  </body>
</html>'''

def html_output(text):
  '''Return html output with unknown words are highlighted.'''
  dict = load_words(DICT)
  return printoutput_and_colorize(dict,text,isHTML=True)

if __name__ == '__main__':
    '''Script called manually, print output to the terminal'''
    if len(sys.argv) < 2:
        print 'usage: uc.py textfile'
        sys.exit(1)

    textf = codecs.open(sys.argv[1], encoding='utf-8')
    text = textf.read()
    textf.close()

    dict = load_words(DICT)
    print printoutput_and_colorize(dict,text,False)
    sys.exit(0)

