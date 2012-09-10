#PunkScanner is a module that sits on top of Wapiti, handles threading etc., and indexes these results to couchdb and Solr
import sys
import traceback
sys.path.append('wapiti-2.2.1/src/')
sys.path.append('pysolr/')
sys.path.append('xmltodict/')
sys.path.append('couchdb/')
import wapiti
import pysolr
import datetime
from lxml import etree
import subprocess
import time
import urlparse

class ParserUploader:
	'''This class takes in a wapiti XML report (usually from a Target object) and uploads it to couchdb'''

	def __init__(self, report, url):
		'''At init, get the sql injectin bugs, xss bugs, and exec bugs. Also have lxml take in the wapiti report given to it.'''

		self.doc = etree.fromstring(report)
		self.url = url
                self.__get_sql()
                self.__get_xss()
                self.__get_bsql()
		self.__reverse_url()

	def __reverse_url(self):

		#starting with http://www.google.com
		out = urlparse.urlparse(self.url)
		#http or https is the first element
		self.protocol = out.scheme
		#www.google.com -> [www,google,com]
		url_list = out.netloc.split(".")
		#list becomes -> [com,google,www]
		url_list.reverse()
		#return com.google.www
		self.url_reversed = ".".join(url_list)

	def __get_sql(self):
		'''Gets the sql injection bugs'''

                sql_bugs = self.doc.xpath("bugTypeList/bugType[@name='SQL Injection']/bugList/bug")
		sql_bugs_dic_list = []

		if sql_bugs:

			for bug in sql_bugs:

				sql_bug_dic = {}
				sql_bug_dic["level"] = bug.get("level")
				sql_bug_dic["url"] = bug.find("url").text.strip()
				sql_bug_dic["parameter"] = bug.find("parameter").text.strip()
				sql_bug_dic["info"] = bug.find("info").text.strip()
				sql_bugs_dic_list.append(sql_bug_dic)

		self.sql_bugs_dic_list = sql_bugs_dic_list

	def __get_xss(self):
		'''Gets the xss bugs'''

                xss_bugs = self.doc.xpath("bugTypeList/bugType[@name='Cross Site Scripting']/bugList/bug")
                xss_bugs_dic_list = []

                if xss_bugs:

                        for bug in xss_bugs:

                                xss_bug_dic = {}
                                xss_bug_dic["level"] = bug.get("level")
                                xss_bug_dic["url"] = bug.find("url").text.strip()
                                xss_bug_dic["parameter"] = bug.find("parameter").text.strip()
                                xss_bug_dic["info"] = bug.find("info").text.strip()
                                xss_bugs_dic_list.append(xss_bug_dic)

                self.xss_bugs_dic_list = xss_bugs_dic_list

        def __get_bsql(self):
                '''Gets the bsql bugs'''

                bsql_bugs = self.doc.xpath("bugTypeList/bugType[@name='Blind SQL Injection']/bugList/bug")
                bsql_bugs_dic_list = []

                if bsql_bugs:

                        for bug in bsql_bugs:

                                bsql_bug_dic = {}
                                bsql_bug_dic["level"] = bug.get("level")
                                bsql_bug_dic["url"] = bug.find("url").text.strip()
                                bsql_bug_dic["parameter"] = bug.find("parameter").text.strip()
                                bsql_bug_dic["info"] = bug.find("info").text.strip()
                                bsql_bugs_dic_list.append(bsql_bug_dic)

                self.bsql_bugs_dic_list = bsql_bugs_dic_list

	def __get_exec(self):
		'''Gets the command execution bugs'''
	
                exec_bugs = self.doc.xpath("bugTypeList/bugType[@name='Commands execution']/bugList/bug")
                exec_bugs_dic_list = []

                if exec_bugs:

                        for bug in exec_bugs:

                                exec_bug_dic = {}
                                exec_bug_dic["level"] = bug.get("level")
                                exec_bug_dic["url"] = bug.find("url").text.strip()
                                exec_bug_dic["parameter"] = bug.find("parameter").text.strip()
                                exec_bug_dic["info"] = bug.find("info").text.strip()
                                exec_bugs_dic_list.append(exec_bug_dic)

                self.exec_bugs_dic_list = exec_bugs_dic_list

	def solr_update(self, n_xss, n_sql, n_bsql):

		conn = pysolr.Solr('http://hg-solr:8080/solr/summary/')
		solr_doc_pull = conn.search("id:" + " \"" + self.url + "\" ")
		vscan_tstamp = datetime.datetime.now()

		for result in solr_doc_pull:
			result["xss"] = n_xss
			result["sqli"] = n_sql
			result["bsqli"] = n_bsql
			result["vscan_tstamp"] = datetime.datetime.now()

		conn.add(solr_doc_pull)

	def solr_details_update(self):
		'''This updates the Solr that will hold all of the bug details'''

		conn = pysolr.Solr('http://hg-solr:8080/solr/detail')
		bug_list_to_index = []
		c = 0 

		for bug in self.xss_bugs_dic_list:

			c = c + 1
			bug_dict = {}
			bug_dict["v_url"] = bug["url"]
			bug_dict["url_main"] = self.url_reversed
			bug_dict["id"] = self.url_reversed + "." + str(c)
			bug_dict["bugtype"] = "xss"
			bug_dict["level"] = bug["level"]
			bug_dict["parameter"] = bug["parameter"]
			bug_dict["info"] = bug["info"]
			bug_dict["protocol"] = self.protocol
			bug_list_to_index.append(bug_dict)

		for bug in self.sql_bugs_dic_list:

			c = c + 1
                        bug_dict = {}
                        bug_dict["v_url"] = bug["url"]
			bug_dict["id"] = self.url_reversed + "." + str(c)
			bug_dict["url_main"] = self.url_reversed
                        bug_dict["bugtype"] = "sqli"
                        bug_dict["level"] = bug["level"]
                        bug_dict["parameter"] = bug["parameter"]
                        bug_dict["info"] = bug["info"]
			bug_dict["protocol"] = self.protocol
			bug_list_to_index.append(bug_dict)

		for bug in self.bsql_bugs_dic_list:

			c = c + 1
                        bug_dict = {}
                        bug_dict["v_url"] = bug["url"]
                        bug_dict["url_main"] = self.url_reversed
			bug_dict["id"] = self.url_reversed + "." + str(c)
                        bug_dict["bugtype"] = "bsqli"
                        bug_dict["level"] = bug["level"]
                        bug_dict["parameter"] = bug["parameter"]
                        bug_dict["info"] = bug["info"]
			bug_dict["protocol"] = self.protocol
			bug_list_to_index.append(bug_dict)

		conn.delete(q="url_main:" + "\"" + self.url_reversed + "\"")
		conn.add(bug_list_to_index)

	def scdb_index(self, manual_override_all_zero = False):
		'''This indexes vulnerabilities to couchdb and updates the timestamp and number of vulns in solr'''

		if manual_override_all_zero == True:

			print "Got manual override, setting all vulnerabilities to 0"
			self.solr_update(0, 0, 0)

		else:

			print "Updating Solr summary..."
			self.solr_update(len(self.xss_bugs_dic_list), len(self.sql_bugs_dic_list), len(self.bsql_bugs_dic_list))

			print "Updating Solr details..."
			if len(self.xss_bugs_dic_list) != 0 or len(self.sql_bugs_dic_list) != 0 or len(self.bsql_bugs_dic_list) != 0:
				self.solr_details_update()
			else:
				print "No bugs found! Skipping indexing to Solr details..."

class PunkSolr():
	'''This class pulls URLs from solr in a variety of ways for later scanning'''

	def __init__(self):

                self.conn = pysolr.Solr("http://hg-solr:8080/solr/summary/")

	def __get_single_site_from_result(self, result):

		for site in result:

			return site		

	def get_not_scanned(self):
		'''get solr records with no vscan timestamp'''
		self.not_scanned = self.conn.search("-vscan_tstamp:*", rows=1)

		return self.not_scanned

	def get_scanned_longest_ago(self):
		'''This gets the record from solr that was scanned longest ago, it starts with those that have no vscan timestamp'''
		scanned_longest_ago_or_not_scanned_dic = self.conn.search('*:*', sort='vscan_tstamp asc', rows=1)

		scanned_longest_ago_or_not_scanned = self.__get_single_site_from_result(scanned_longest_ago_or_not_scanned_dic)

		return scanned_longest_ago_or_not_scanned

class Target():
	'''This class holds a target object and performs the actual scan. Once a scan is performed the result is a wapiti XML report'''

	def __init__(self):

		self.punk_solr = PunkSolr()
		self.timestamp = datetime.datetime.now()
                self.conn = pysolr.Solr('http://hg-solr:8080/solr/summary/')

	def set_url(self, url, outfile):

		self.url = url
		self.opt_list = [('-o', outfile), ('-f', 'xml'), ('-b', 'domain'), ('-v', '2'), ('-u', ''), ('-n', '1'), ('-t', '25'),\
#!		('-m', '-all,xss:get,sql:get,blindsql:get')]
		('-m', '-all,xss:get,sql:get'), ('-p','tor://127.0.0.1:9066')]

	def update_vscan_tstamp(self):

                solr_doc_pull = self.conn.search("id:" + " \"" + self.url + "\" ")
                vscan_tstamp = datetime.datetime.now()

                for result in solr_doc_pull:
                        result["vscan_tstamp"] = datetime.datetime.now()

                self.conn.add(solr_doc_pull)

	def delete_vscan_tstamp(self):

                solr_doc_pull = self.conn.search("id:" + " \"" + self.url + "\" ")

                for result in solr_doc_pull:
                        del result["vscan_tstamp"]

                self.conn.add(solr_doc_pull)

	def delete_record(self):

                out = urlparse.urlparse(self.url)
                netlocation = out.netloc

		self.conn.delete(q = "url:" + " \"" + netlocation + "\" ")

	def punk_scan(self):
		'''This performs the actual scan. Note that the timestamp is updated before the scan starts, this makes it such that other scanners
		know this is being scanned before it finishes the scanning. Reduces number of duplicate scans'''

		wap = wapiti.Wapiti(self.url)		
		return wap.scan(self.url, self.opt_list)

if __name__ == "__main__":

	total_time_sec = 0
	sites_scanned = 0
	sites_failed = 0

	while True:

		start_scan = datetime.datetime.now()
		print "\n\n***getting a new website to scan***\n\n"
		site_to_scan = PunkSolr().get_scanned_longest_ago() 
		print site_to_scan

		target = Target()
		target.set_url(site_to_scan['url'], 'out.xml')
		target.update_vscan_tstamp()

		try:
			scan_result = target.punk_scan()

		except:

			print "scan failed once, trying the scan again"
			traceback.print_exc(file=sys.stdout)

			try:
				scan_result = target.punk_scan()

			except:
			
				traceback.print_exc(file=sys.stdout)
				print "Scan failed for a second time, leaving it as is, with no results"
				sites_failed = sites_failed + 1
				continue

                scan_url = target.url
    		ParserUploader(scan_result, scan_url).scdb_index()

                end_scan = datetime.datetime.now()
                scan_time_delta = end_scan - start_scan
                scan_time_sec = scan_time_delta.total_seconds()
                scan_time = scan_time_sec/60

                print "Scan took %s minutes to run." % str(scan_time)
                sites_scanned = sites_scanned + 1
                total_time_sec = total_time_sec + scan_time_sec
                total_time = total_time_sec/86400
                avg_rate = sites_scanned/total_time

                print "%s sites scanned so far. That's a rate of %s sites per day" % (str(sites_scanned), str(avg_rate))
		print "finished scanning successfully"
		print "*****So far %s sites have failed to scan*****" % str(sites_failed)
