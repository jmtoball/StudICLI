#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Johannes Maximimilian Toball"
__license__ = "by-sa"

import re

def br2nl(pqObject):
	""" Replaces <br>-tags with newlines to maintain formatting when extracting the text from html."""
	pqObject.children("br").replaceWith("\n\r")
	return pqObject

def fromQueryString(query, attr):
	""" Extracts the value of an attribute from a querystring"""
	try:
		return re.search(attr+"=(\w+)[&$#]*", query).group(1)
	except:
		return ""

def selectId(type, max):
	""" Prompt helper for index inputs """
	success = False
	while not success:
		try:
			id = int(raw_input(type+" über die Nummer in Klammern wählen: "))
			if id > max or id < 0:
				print "Ein Eintrag mit dieser ID existiert nicht"
				continue
		except ValueError:
			print "Die ID muss eine Zahl sein"
			continue
		success = True
	return id
