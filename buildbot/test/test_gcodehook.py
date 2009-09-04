# -*- test-case-name: buildbot.test.test_gcodehook -*-

from twisted.trial import unittest
from buildbot.changes.gcodehook import GoogleCodeHook
from buildbot.changes.svnpoller import split_file_branches

from StringIO import StringIO
import simplejson
import time

class MyGCodeHook(GoogleCodeHook):
    def __init__(self, *args, **kwargs):
        GoogleCodeHook.__init__(self, *args, **kwargs)
        self.changes = []

    def createWebServer(self, http_port, handler):
        pass

    def addChange(self, change):
        self.changes.append(change)

class FakeReq(object):
    def __init__(self, content):
        self.content = StringIO(content)
        self.response_code = None

    def setResponseCode(self, code):
        self.response_code = code

    def setHeader(self, name, value):
        pass

def makeJson(revisions):
    data = {
        "repository_path": "http://example.googlecode.com/svn/",
        "project_name": "example",
        "revisions": []
    }
    for rev in revisions:
        for key in ['added', 'modified', 'removed']:
            if key not in rev:
                rev[key] = []
        if 'author' not in rev:
            rev['author'] = "example"
        if 'timestamp' not in rev:
            rev['timestamp'] = int(time.time())
        if 'url' not in rev:
            rev['url'] = "http://example.googlecode.com/svn-history/r%d/" % rev['revision']

        data['revisions'].append(rev)

    data['revision_count'] = len(revisions)

    return simplejson.dumps(data)

class BasicTest(unittest.TestCase):
    def testNoBranches(self):
        g = MyGCodeHook(http_port=None)

        json = makeJson([{
            'message': 'Initial test',
            'added': ['trunk/file1.cpp'],
            'revision': 2
        }])

        req = FakeReq(json)
        g.handler.render_POST(req)

        self.assertEqual(req.response_code, 200)

        self.assertEqual(len(g.changes), 1)
        self.assertEqual(g.changes[0].files, ["trunk/file1.cpp"])
        self.assertEqual(g.changes[0].revision, 2)
        self.assertEqual(g.changes[0].comments, "Initial test")

    def testTrunkExtract(self):
        g = MyGCodeHook(http_port=None, split_file=split_file_branches)

        json = makeJson([{
            'message': 'Initial test',
            'added': ['trunk/file1.cpp'],
            'revision': 2
        }])

        req = FakeReq(json)
        g.handler.render_POST(req)

        self.assertEqual(req.response_code, 200)

        self.assertEqual(len(g.changes), 1)
        self.assertEqual(g.changes[0].files, ["file1.cpp"])
        self.assertEqual(g.changes[0].branch, None)
        self.assertEqual(g.changes[0].revision, 2)
        self.assertEqual(g.changes[0].comments, "Initial test")

    def testBranchExtract(self):
        g = MyGCodeHook(http_port=None, split_file=split_file_branches)
        json = makeJson([{
            'message': 'Branch commit',
            'added': ['branches/foo/file1.cpp'],
            'revision': 3
        }])
        req = FakeReq(json)
        g.handler.render_POST(req)

        self.assertEqual(req.response_code, 200)

        self.assertEqual(len(g.changes), 1)
        self.assertEqual(g.changes[0].files, ["file1.cpp"])
        self.assertEqual(g.changes[0].branch, "branches/foo")
        self.assertEqual(g.changes[0].revision, 3)
        self.assertEqual(g.changes[0].comments, "Branch commit")
