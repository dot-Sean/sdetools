Convert a mapping in Fortify from a rules file to our standard task->cwe mapping

NOTE: In this case we don't have a CWE ID - but we do have a weakness category.

Copy the output to sdetools/docs/fortify/sde_fortify_map.xml


**** command line ****
 xsltproc fortify.xsl rules-file.xml | xmlindent

