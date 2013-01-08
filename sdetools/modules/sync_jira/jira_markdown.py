import re

def convert_markdown(c):
    # replace all links
    # c = re.sub(r'\[([^\]]+)\]\(([^\]]+)\)', r'[\1|\2]', c)
    c = re.sub(r'\[(.*?)\]\((.*?)\)', r'[\1|\2]', c)

    # replace bold temporarily
    c = re.sub(r'\*\*(.*?)\*\*', r'bdirkb\1bdirkb', c)
    # replace italics
    c = re.sub(r'\*(.*?)\*', r'_\1_', c)
    # replace bold
    c = re.sub(r'bdirkb(.*?)bdirkb', r'*\1*', c)

    # replace inline code
    c = re.sub(r'`(.*?)`', r'*\1*', c)

    # print c
    c = c.split('\n')

    words = []
    # We step down on the levels to keep things nice
    words.append( ['#','h3.'] )
    words.append( ['##','h4.'] )
    words.append( ['###','h5.'] )
    words.append( ['####','h6.'] )
    words.append( ['#####','h6.'] )
    words.append( ['######','h6.'] )

    new_content = []

    i = 0
    is_code = 0
    indent = 0
    is_quote = 0
    is_list = 0

    for l in c:
      i += 1
      if 0 == 0:
        # print l[:30]
        k = l
        if l[0:1]=='*':
          is_list = 1
        if l == '':
          is_list = 0

        if l[0:1] == '>':
          if is_quote==0:
            k = '{quote}\n'+k[1:]
            is_quote = 1
          else:
            k = k[1:]


        if is_list == 0:
          if is_code == 1:
            if l[0:1] == ' ' or l[0:1]=='\t':
              k = k[indent:]
            else:
              k = '{code}\n'+k
              is_code = 0
              indent = -1
          else:
            if l[0:1]==' ' or l[0:1]=='\t':
              indent = len(k)-len(k.lstrip())
              k = '{code}\n'+k[indent:]
              is_code = 1
        else:
           if l[0:4]=='\t\t\t*':
             k = '****' + l[4:]
           if l[0:3]=='\t\t*':
             k = '***' + l[3:]
           if l[0:2]=='\t*':
             k = '**' + l[2:]

        for w in words:
          if l[:len(w[0])] == w[0]:
            k = w[1]+l[len(w[0]):]


        if l[0:1] != '>' and is_quote == 1:
          k = '{quote}\n'+k
          is_quote = 0


        if l[0:3] != '| -':
          new_content.append(k)

    return '\n'.join(new_content)
