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
        Net.__init__(self, cookie_file=cookie_file)
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
                        self._resolve_cloudflare(url, challenge, form_data, headers, compression)
                        helper.log_debug("Successfully resolved cloudflare challenge, fetching real response")
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

        try:
            helper.log_debug("Attempting to resolve the challenge")
            response = Net._fetch(self, query, form_data, headers, compression)
            helper.log_debug("Resolved the challenge, updating cookies")
            for c in self._cloudflare_jar:
                self._cj.set_cookie(c)
            self._update_opener()
        except urllib2.HTTPError as e:
            helper.log_debug("Failed to resolve the cloudflare challenge with exception %s" % str(e))
            self._update_opener()
            pass
        helper.end('_resolve_cloudflare')
    
    def _get_cloudflare_answer(self, url, challenge, form_data={}, headers={}, compression=True):
        '''
            Use the cloudflare cookie jar to overcome the cloudflare challenge.
            Returns an URL with the answer to try.

            Credit to lambda - https://offshoregit.com/lambda81/
            plugin.video.genesis\resources\lib\libraries\cloudflare.py        
        '''
        helper.start("_get_cloudflare_answer")
        if not challenge:
            helper.log_debug('Challenge is empty, re')
            raise ValueError('Challenge is empty')

        import re
        try:
            jschl = re.compile('name="jschl_vc" value="(.+?)"/>').findall(challenge)[0]
            init_str = re.compile('setTimeout\(function\(\){\s*.*?.*:(.*?)};').findall(challenge)[0]
            builder = re.compile(r"challenge-form\'\);\s*(.*)a.v").findall(challenge)[0]
            decrypt_val = self._parseJSString(init_str)
            lines = builder.split(';')
        except Exception as e:
            helper.log_debug('Failed to parse the challenge %s' % str(challenge))
            lines = []
            raise

        try:
            for line in lines:
                if len(line) > 0 and '=' in line:
                    sections = line.split('=')
                    line_val = self._parseJSString(sections[1])
                    decrypt_val = int(eval(str(decrypt_val) + sections[0][-1] + str(line_val)))
        except Exception as e:
            helper.log_debug('Failed to find the decrypt_val from the lines')
            raise

        from urlparse import urlparse
        path = urlparse(url).path
        netloc = urlparse(url).netloc
        if not netloc:
            netloc = path

        answer = decrypt_val + len(netloc)

        url = url.rstrip('/')
        query = '%s/cdn-cgi/l/chk_jschl?jschl_vc=%s&jschl_answer=%s' % (url, jschl, answer)

        import urllib
        if 'type="hidden" name="pass"' in challenge:
            passval = re.compile('name="pass" value="(.*?)"').findall(challenge)[0]
            query = '%s/cdn-cgi/l/chk_jschl?pass=%s&jschl_vc=%s&jschl_answer=%s' % \
                    (url, urllib.quote_plus(passval), jschl, answer)
            import time
            time.sleep(9)

        helper.end("_get_cloudflare_answer")
        return query

    def _parseJSString(self, s):
        '''
            Credit to lambda - https://offshoregit.com/lambda81/
            plugin.video.genesis\resources\lib\libraries\cloudflare.py        
        '''
        try:
            offset=1 if s[0] == '+' else 0
            val = int(eval(s.replace('!+[]','1').replace('!![]','1').replace('[]','0').replace('(','str(')[offset:]))
            return val
        except Exception as e:
            helper.log_debug('_parseJSString failed with exception %s' % str(e))
            pass

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