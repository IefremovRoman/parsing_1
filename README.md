# Requests+bs4 parser
Internet store parsing practice using bs4 and requests libraries

This is internet store parser. Here we collect some data like ULR, name, description, characteristics, imageURLs etc. It is built with requsts and bs4 libraries as main engines. Parser made with using proxy rotating with proxyscrape in its base. I admit that here we will not encounter with js, instead parser will go to infinite while loop. Sometimes it happens with this commit...

Structure of the project: 
Main recursion function, that collects site "tree"-like category structure:
  Proxy rotating engine. 
  Scrap controller, which takes items from end category: 
    Max page numbers to control iterating throught category pages. 
    Collector links from each page. 
    Item collector, which scrapes data from each product. 
Excel write function writes every category to .xlsx.
