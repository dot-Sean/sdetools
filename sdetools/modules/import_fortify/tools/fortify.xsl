<?xml version="1.0"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="xml" indent="yes"/>
<xsl:template match="ExternalMetadataPack">
<mapping>
    <xsl:apply-templates/>
</mapping>
</xsl:template>
<xsl:template match="Mapping">
<task>
    <xsl:attribute name="id">
        <xsl:value-of select="substring-after(substring-before(ExternalCategory,':'),'T')"/>
    </xsl:attribute>
    <xsl:attribute name="title">
        <xsl:value-of select="substring-after(ExternalCategory,': ')"/>
    </xsl:attribute>
    
    <cwe>
    <xsl:attribute name="id">
        <xsl:value-of select="InternalCategory"/>
    </xsl:attribute>
    <xsl:attribute name="title">
        <xsl:value-of select="InternalCategory"/>
    </xsl:attribute>
    </cwe>
</task>
</xsl:template>
  <xsl:template match="node()|@*">
    <xsl:apply-templates select="node()|@*"/>
  </xsl:template>
</xsl:stylesheet>


