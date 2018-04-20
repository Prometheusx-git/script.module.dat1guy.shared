# -*- coding: utf-8 -*-
'''
    dat1guy's Shared Methods - a plugin for Kodi
    Copyright (C) 2016 dat1guy

    This file is part of dat1guy's Shared Methods.

    dat1guy's Shared Methods is free software: you can redistribute it and/or
    modify it under the terms of the GNU General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    dat1guy's Shared Methods is distributed in the hope that it will be 
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with dat1guy's Shared Methods.  If not, see 
    <http://www.gnu.org/licenses/>.
'''


import urllib2, cookielib 
from addon.common.net import Net
from dat1guy.shared.shared_helper import shared_helper as helper
from time import sleep
import re
from decimal import Decimal, ROUND_UP

class NetHelper(Net):
    '''
        The Net class is extended to get around the site's usage of cloudflare.
        Credit goes to lambda.  The idea is to use a separate cookie jar to
        pass cloudflare's "challenge".
    '''

    # PYTHON 2.6 BUG: ISSUE #5537 (http://bugs.python.org/issue5537)
    # SWITCH TO MOZILLA COOKIE JAR FROM LWP COOKIE JAR
    Net._cj = cookielib.MozillaCookieJar()
    
    def __init__(self, cookie_file, cloudflare=False):
        user_agent = 'Mozilla/5.0 (Linux; Android 4.0.4; Galaxy Nexus Build/IMM76B) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.133 Mobile Safari/535.19'	
        Net.__init__(self, cookie_file=cookie_file, user_agent=user_agent)
        self._cloudflare_jar = cookielib.MozillaCookieJar() # ISSUE #5537
        self._cloudflare = cloudflare

    def _fetch(self, url, form_data={}, headers={}, compression=True):
        '''
            A wrapper around the super's _fetch with cloudflare support
        '''
        helper.log_debug("Fetch attempt url: %s, form_data: %s, headers: %s" % (url, form_data, headers))
        if not self._cloudflare:
            return Net._fetch(self, url, form_data, headers, compression)
        else:
            try:
                r = Net._fetch(self, url, form_data, headers, compression)
                helper.log_debug('Did not encounter a cloudflare challenge')
                return r
            except urllib2.HTTPError as e:
                if e.code == 503:
                    helper.log_debug('Encountered a cloudflare challenge')
                    challenge = e.read()
                
                    if challenge == 'The service is unavailable.':
                        helper.log_debug('Challenge says the service is unavailable')
                        raise
                    try:
                        helper.log_debug("Received a challenge, so we'll need to get around cloudflare")
                        #helper.show_error_dialog(['',str(challenge)])						
                        self._resolve_cloudflare(url, challenge, form_data, headers, compression)
                        helper.log_debug("Successfully resolved cloudflare challenge, fetching real response")
                        #helper.show_error_dialog(['',str(url)])  
                        return Net._fetch(self, url, form_data, headers, compression)
                    except urllib2.HTTPError as e:
                        helper.log_debug("Failed to set up cloudflare with exception %s" % str(e))
  
                        raise
                else:
                    helper.log_debug('Initial attempt failed with code %d' % e.code)
                    raise

    def _resolve_cloudflare(self, url, challenge, form_data={}, headers={}, compression=True):
        """
            Asks _cloudflare for an URL with the answer to overcome the 
            challenge, and then attempts the resolution.
        """
        helper.start("_resolve_cloudflare")
        from urlparse import urlparse, urlunparse
        parsed_url = urlparse(url)
        cloudflare_url = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
        query = self._get_cloudflare_answer(cloudflare_url, challenge, form_data, headers, compression)

        # Use the cloudflare jar instead for this attempt; revert back to 
        # main jar after attempt with call to update_opener()
        self._update_opener_with_cloudflare()
		
        #helper.show_error_dialog(['',str(self._cloudflare_jar)])		
        response,error = self.get_html(query, self._cloudflare_jar,headers, form_data)#Net._fetch(self, query, form_data, headers, compression)
        		
        helper.log_debug("Resolved the challenge, updating cookies")
        for c in self._cloudflare_jar:
            self._cj.set_cookie(c)
        self._update_opener()
        helper.end('_resolve_cloudflare')
    
    def _get_cloudflare_answer(self, url, challenge, form_data={}, headers={}, compression=True):
        '''     
        '''
        helper.start("_get_cloudflare_answer")
        self.js_data = {}	
        #self.header_data = {}
		
        if not challenge:
            helper.log_debug('Challenge is empty, re')
            raise ValueError('Challenge is empty')
		
        if not "var s,t,o,p,b,r,e,a,k,i,n,g,f" in challenge:
            return		
			
        try:
            self.js_data["auth_url"] = \
                re.compile('<form id="challenge-form" action="([^"]+)" method="get">').findall(challenge)[0]
            self.js_data["params"] = {}
            self.js_data["params"]["jschl_vc"] = \
                re.compile('<input type="hidden" name="jschl_vc" value="([^"]+)"/>').findall(challenge)[0]
            self.js_data["params"]["pass"] = \
                re.compile('<input type="hidden" name="pass" value="([^"]+)"/>').findall(challenge)[0]
            var, self.js_data["value"] = \
                re.compile('var s,t,o,p,b,r,e,a,k,i,n,g,f[^:]+"([^"]+)":([^\n]+)};', re.DOTALL).findall(challenge)[0]
            self.js_data["op"] = re.compile(var + "([\+|\-|\*|\/])=([^;]+)", re.MULTILINE).findall(challenge)
            self.js_data["wait"] = int(re.compile("\}, ([\d]+)\);", re.MULTILINE).findall(challenge)[0]) / 1000
			
        except Exception as e:
            helper.log_debug("Error executing Cloudflare IUAM Javascript. %s" % str(challenge))
            self.js_data = {}			
            #raise
			
        if "refresh" in (headers):			
            helper.show_error_dialog(['',str(headers)])
			
        if self.js_data.get("wait", 0):		
            jschl_answer = self.decode2(self.js_data["value"])

            for op, v in self.js_data["op"]:
                # jschl_answer = eval(str(jschl_answer) + op + str(self.decode2(v)))
                if op == '+':
                    jschl_answer = jschl_answer + self.decode2(v)
                elif op == '-':
                    jschl_answer = jschl_answer - self.decode2(v)
                elif op == '*':
                    jschl_answer = jschl_answer * self.decode2(v)
                elif op == '/':
                    jschl_answer = jschl_answer / self.decode2(v)

            from urlparse import urlparse
            path = urlparse(url).path
            netloc = urlparse(url).netloc
            if not netloc:
                netloc = path													
				
            self.js_data["params"]["jschl_answer"] = round(jschl_answer, 10) + len(netloc)		

            url = url.rstrip('/')
            import urllib        
            query = '%s%s?%s' % (
                url, self.js_data["auth_url"], urllib.urlencode(self.js_data["params"]))
            #helper.show_error_dialog(['',str(query)]) 		
				
            sleep(self.js_data["wait"])
            #sleep(5)	
            helper.end("_get_cloudflare_answer")
            return query
        #helper.show_error_dialog(['',str(answer)]) 
			
    def decode2(self, data):
        data = re.sub("\!\+\[\]", "1", data)
        data = re.sub("\!\!\[\]", "1", data)
        data = re.sub("\[\]", "0", data)

        pos = data.find("/")
        numerador = data[:pos]
        denominador = data[pos + 1:]

        aux = re.compile('\(([0-9\+]+)\)').findall(numerador)
        num1 = ""
        for n in aux:
            num1 += str(eval(n))

        aux = re.compile('\(([0-9\+]+)\)').findall(denominador)
        num2 = ""
        for n in aux:
            num2 += str(eval(n))

        # return float(num1) / float(num2)
        # return Decimal(Decimal(num1) / Decimal(num2)).quantize(Decimal('.0000000000000001'), rounding=ROUND_UP)
        return Decimal(Decimal(num1) / Decimal(num2)).quantize(Decimal('.0000000000000001'))
				

    def _update_opener_with_cloudflare(self):
        '''
            Uses the cloudflare jar temporarily for opening future links. 
            Revert back to the main jar by invoking _update_opener().
        '''
        tmp_jar = self._cj
        self._cloudflare_jar = cookielib.LWPCookieJar()
        self._cj = self._cloudflare_jar
        Net._update_opener(self)
        self._cj = tmp_jar
        return

    def get_html(self, url, cookies, referer, form_data=None):
        html, html_exception = '', None
        try:
            self.set_cookies(cookies)
            helper.log_debug('Performing a %s operation' % ('POST' if form_data else 'GET'))
            if form_data:
                html = self.http_POST(url, form_data, headers={'Referer':referer}).content
            else:
                html = self.http_GET(url, headers={'Referer':referer}).content
            if html != '':
                helper.log_debug("Saving cookies")
                self.save_cookies(cookies)
            helper.log_debug("Operation complete")
        except Exception as e:
            html_exception = e

        if helper.debug_dump_html():
            helper.log_debug('HTML DUMP: %s' % html)
        
        return (html, html_exception)

    def refresh_cookies(self, cookies):
        import xbmcvfs
        if xbmcvfs.exists(cookies):
            xbmcvfs.delete(cookies)
        cookiesfile = xbmcvfs.File(cookies, 'w')
        cookiesfile.write('#LWP-Cookies-2.0\n')
        cookiesfile.close()

    def get_json(self, url, cookies, referer, form_data=None):
        ajax_response, e = self.get_html(url, cookies, referer, form_data)
        import simplejson
        json = simplejson.loads(ajax_response)

        if helper.debug_dump_html():
            helper.log_debug('JSON DUMP: %s' % json)
        
        return json