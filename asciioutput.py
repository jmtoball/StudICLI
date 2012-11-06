#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Johannes Maximimilian Toball"
__license__ = "by-sa"

from textwrap import TextWrapper 

class ASCIIOutput:
	""" Helps formatting output for the commandline """
	
	def __init__(self, width=80):
		""" Sets up the class and configures the utilized Textwrapper-object"""
		self.width = width
		wrapper = TextWrapper()
		wrapper.width = width	
		wrapper.replace_whitespace = False	
		wrapper.drop_whitespace = False	
		self.wrapper = wrapper

	def trim(self, string):
		""" trims a string down to the predefined width """
		width = self.width
		trimmed = string[:min(width-8, len(string))]
		if len(trimmed) != len(string):
			return trimmed+"..."
		else:
			return string

	def h1(self, text, noOutput=False):
		""" outputs text justified and surrounded by a border to underline its importance."""
		width = self.width
		output = ("#"*width)+"\n"
		output += "# "+self.trim(text).ljust(width-3,"/" )+"#\n"
		output += "#"*width
		if noOutput:
			return output
		print output

	def h2(self, text, noOutput=False):
		""" outputs text justified and surrounded by a border to underline its importance,
			though not as much as h1() does."""
		width = self.width
		output = "+"+("-"*(width-2))+"+\n"
		output += "| "+self.trim(text).ljust(width-4)+" |\n"
		output += "+"+("-"*(width-2))+"+"
		if noOutput:
			return output
		print output
	
	def h3(self, text, noOutput=False):
		""" makes the text stand out a little more. """
		output = text+":\n"
		output = self.trim(output)
		if noOutput:
			return output
		print output
	
	def text(self, text, noOutput=False):
		""" wraps the text so it does not exceed the alowed number of characters per line """
		width = self.width
		output = self.wrapper.fill(text)
		if noOutput:
			return output
		print output

	def hr(self, noOutput=False):
		""" draws a horizonatl rule with the predefined length"""
		width = self.width
		output = "-"*width
		if noOutput:
			return output
		print output
