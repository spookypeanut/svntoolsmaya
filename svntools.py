import maya.cmds as mc
import os, re, string as str, pickle
import pysvn, xml.dom.minidom

myrepos = ""
mycheckout = ""

cfgfilename = '/cgstaff/hbush/maya/scripts/svntools.cfg'

HBlistbox = ""
HBmainwin = ""

class checkedout:
	"This class holds details of the local version of a file"
	def __init__(self, passedrepos):
		self.repos = passedrepos
		self.assetname = "jonboy"
		self.projectname = "monkeyproject"
		self.localdir = "/cgstaff/hbush/svntemp/" + self.projectname
		self.client = pysvn.Client()
		if os.path.isfile(cfgfilename):
			self.readcfg()

	def readcfg(self):
		f = open(cfgfilename, 'r')
		self.repos = pickle.load(f)

	def writecfg(self):
		f = open(cfgfilename, 'w')
		pickle.dump(self.repos, f)

	def filename(self):
		return self.localdir + '/' + self.assetname + '/' + self.projectname + '.' + self.assetname + '.ma'


	def revlist(self, what):
		HBheadrev = pysvn.Revision(pysvn.opt_revision_kind.head)
		HBcurrrev = HBheadrev
		HBalllogs = self.client.log(self.filename())
		self.listwin = mc.window()
		HBwindwidth=600
		HBwindheight=300
		mc.window(self.listwin, edit = True, widthHeight = [HBwindwidth, HBwindheight])
		HBcolumns = mc.columnLayout(columnAttach = ('both', 5), columnWidth = HBwindwidth)
		HBrevlist = []
		HBcount = 0
		for HBentrydict in HBalllogs:
			HBstring="Revision %d by %s - %s" % (HBentrydict['revision'].number, HBentrydict['author'], HBentrydict['message'])
			print HBstring
			HBrevlist.append(HBstring)
			HBcount = HBcount + 1
		self.revlistbox = mc.textScrollList(numberOfRows = HBcount, append = HBrevlist)
		HBgrids = mc.gridLayout (numberOfColumns = 2, cellWidthHeight=(100, 50))
		mc.button(label = "OK", command = self.revlistcall)
		mc.button(label = "Cancel", command = self.revlistclose)
		mc.showWindow(self.listwin)

	def revlistclose(self, result):
		mc.deleteUI(self.listwin)

	def revlistcall(self, result):
		selected = mc.textScrollList(self.revlistbox, q = True, selectItem = True)[0]
		revnum = selected.split()[1]
		print revnum
		self.checkout(int(revnum))
		self.revlistclose(0)

	def coyoung(self, ignored):
		self.checkout(0)

	def cfgwin(self, ignored):
		self.cfgwin = configwin(self)

	def checkout(self, revnum = 0):
		HBfilename = self.filename()
		if not os.path.exists(self.localdir):
			os.makedirs(self.localdir)
		if isversioned(HBfilename):
			diffsdump = self.client.diff("temp_diff_files", HBfilename) 
			if (mc.file(q = True, anyModified = True)) or (diffsdump != ""):
				if mc.file(q = True, anyModified = True) and (diffsdump != ""):
					middle = "both within Maya and to\n\"" + HBfilename + "\"\n on disc" 
				elif diffsdump != "":
					middle = "to\n\"" + HBfilename + "\"\n on disc"
				else:
					middle = "within Maya"

				promptMessage = "You have made changes " + middle + " without committing them.\nAre you sure you want to discard your changes?"
				HBresult = mc.confirmDialog(title = "Please confirm",\
					message = promptMessage, button = ['OK', 'Cancel'],\
					defaultButton = 'Cancel', cancelButton = 'Cancel', dismissString = 'Cancel')
				if HBresult == 'Cancel':
					return -1
			if not self.client.info(self.localdir).url == self.repos.url:
				print "Switching..."
				rmrec(self.localdir)
		else:
			print "File not currently under version control"
		if os.path.isfile(HBfilename):
			os.remove(HBfilename)
		if revnum != 0:
			print "Checking out revision number %d" % revnum
			HBrev = pysvn.Revision(pysvn.opt_revision_kind.number, revnum)
			self.client.checkout(self.repos.url, self.localdir, revision = HBrev)
		else:
			print "Checking out youngest revision"
			self.client.checkout(self.repos.url, self.localdir)
		#comment = self.svnislocked()
		#if (comment):
			#print '%s is locked' % HBfilename 
			#print "The comment says \"%s\"" % comment
			#return 0
		#else:
			#print "%s is not locked, locking..." % HBfilename
			#HBresult = mc.promptDialog(title = "Enter lock message",\
				#message = "Please enter your reason for locking the file", button = ['OK', 'Don\'t lock'],\
				#defaultButton = 'OK', cancelButton = 'Don\'t lock', dismissString = 'Don\'t lock')
			#if HBresult == 'OK':
				#HBlockmessage = mc.promptDialog(q = True, text = True)
				#self.client.lock(HBfilename, HBlockmessage)
			#else:
				#HBanswer = mc.confirmDialog(title = "Warning", \
					#message = "File NOT locked. Do NOT make any changes", \
					#button = "OK", defaultButton = "OK", cancelButton = "OK", \
					#dismissString = "OK")
			#mc.file(self.filename(), o = True, force = True)
			
	#def svnislocked(self):
		#print "Checking lock..."
		#HBfilename = self.filename()
		#HBinfodump = self.client.info2 (HBfilename, recurse=False)
		#print HBinfodump
		#for path, info in HBinfodump:
			#print "path = " + path 
			#if info['lock']:
				#print "Locked"
				#if info['lock']['token'] != '':
					#print "Locked 2"
					#if info['lock']['owner'] == os.environ['USER']:
						#print "Locked by current user: unlocking..."
						#self.client.unlock(HBfilename)
						#return 0
					#else:
						#print info['lock']['comment']
						#return info['lock']['comment']
		#return 0

	def discard(self, ignored):
		HBfilename=self.filename()
		HBanswer = mc.confirmDialog(title = "Discard changes?", \
					message = "Discard all changes and reload last committed version?", \
					button = ["Yes", "No"], defaultButton = "No", cancelButton = "No", \
					dismissString = "No")
		if HBanswer == "Yes":
			print "Reverting..."
			HBfilename = self.filename()
			#self.client.unlock(HBfilename)
			self.client.revert(HBfilename)
			if (mc.file(HBfilename, open = True, force = True)):
				return 1
			else:
				return 0
		else:
			print "Cancelled"
			return 0

def rmrec(dirname):
	if not os.path.isdir(dirname):
		return 0
	if not os.access(dirname, os.W_OK):
		return 0
	for root, dirs, files in os.walk(dirname, topdown = False):
		print root
		for eachfile in files:
			os.remove(root + "/" + eachfile)
		os.rmdir(root)

def isversioned(checkfile):
	HBclient = pysvn.Client()
	dironly = re.compile('[^/]*$')
	HBdirname = dironly.sub('', checkfile)
	if not os.path.exists(HBdirname + ".svn"):
		print "No .svn directory: assuming unversioned"
		return 0
	return HBclient.status(checkfile)[0].is_versioned

class repos:
	"All the details for a repository are stored in here"
	def __init__(self):
		self.protocol = "svn+ssh"
		self.hostname = "wg09henry"
		self.dir = "/cgstaff/hbush/.repos/"
		self.name = "svntest"
		self.updateurl()

	def updateurl(self):
		self.url = self.protocol + "://" + self.hostname + self.dir + self.name

class configwin:
	"Creates a config window"
	def __init__(self, mycheckout):
		self.checkout = mycheckout
		self.repos = mycheckout.repos
		self.winref = mc.window()
		HBwindwidth=400
		HBwindheight=600
		mc.window(self.winref, edit = True, height = HBwindheight, width = HBwindwidth, title = "SVN Tools Config")

		HBtabs = mc.tabLayout()
		HBcolumns = mc.columnLayout(adjustableColumn = True)
		mc.tabLayout(HBtabs, edit = True, tabLabel = (HBcolumns, "Repository"))
		self.urldisplay = mc.text (label = self.repos.url, align = "center")
		self.repos.updateurl()
		
		HBgrids = mc.gridLayout (numberOfColumns = 2, cellWidthHeight=(200, 120))
		mc.frameLayout(label = "Protocol")
		HBmorecolumns = mc.columnLayout(columnAttach=('left', 30), columnWidth=10, adjustableColumn = True)
		self.protfield = mc.radioCollection();
		self.protsvn = mc.radioButton(label = "svn", align = 'left', onCommand = self.changeprot)
		self.protssh = mc.radioButton(label = "svn+ssh", align = 'left', onCommand = self.changeprot)
		self.prothttp = mc.radioButton(label = "http", align = 'left', onCommand = self.changeprot)
		self.prothttps = mc.radioButton(label = "https", align = 'left', onCommand = self.changeprot)
		
		mc.setParent(HBgrids)
		mc.frameLayout(label = "Hostname")
		self.hostnamefield = mc.textField(editable = True, text = self.repos.hostname)
		mc.textField(self.hostnamefield, edit = True, cc = self.changehost)
		
		mc.setParent(HBgrids)
		mc.frameLayout(label = "Path to repository")
		self.reposdirfield = mc.textField(editable = True, text = self.repos.dir)
		mc.textField(self.reposdirfield, edit = True, cc = self.changereposdir)
		
		mc.setParent(HBgrids)
		mc.frameLayout(label = "Repository name")
		self.reposnamefield = mc.textField(editable = True, text = self.repos.name)
		mc.textField(self.reposnamefield, edit = True, cc = self.changereposname)

		mc.showWindow(self.winref)
		mc.window(self.winref, edit = True, height = HBwindheight, width = HBwindwidth)

	def printurl(self):
		self.repos.updateurl()
		mc.text(self.urldisplay, edit = True, label = self.repos.url)

	def changereposname(self, newname):
		self.repos.name = newname
		self.somethingchanged()

	def changereposdir(self, newdir):
		print newdir
		if newdir[len(newdir)-1] != '/':
			newdir = newdir + '/'
		self.repos.dir = newdir
		self.somethingchanged()
		
	def changehost(self, newname):
		self.repos.hostname = newname
		self.somethingchanged()

	def changeprot(self, newprot):
		currentsetting = mc.radioCollection(self.protfield, query = True, select = True)
		switch = {
			self.protsvn.split('''|''')[len(self.protsvn.split('''|'''))-1]: 'svn',
			self.protssh.split('''|''')[len(self.protsvn.split('''|'''))-1]: 'svn+ssh',
			self.prothttp.split('''|''')[len(self.protsvn.split('''|'''))-1]: 'http',
			self.prothttps.split('''|''')[len(self.protsvn.split('''|'''))-1]: 'https',
		}
		self.repos.protocol = switch [currentsetting]
		self.somethingchanged()

	def somethingchanged(self):
		self.printurl()
		self.checkout.writecfg()

class mainwindow:
	"Creates the main window"
	def __init__(self, passedcheckout):
		HBwindwidth = 300
		HBwindheight = 500
		self.checkout = passedcheckout
		HBmainwin = mc.window()
		mc.window(HBmainwin, edit = True, height = HBwindheight, width = HBwindwidth, title = "SVN Tools for Maya")
		HBcolumns = mc.columnLayout(adjustableColumn = True)
		mc.button(label = "svncheckout(0)", align="center", command = self.checkout.coyoung, width=HBwindwidth)
		mc.button(label = "svncorev", align="center", command = self.checkout.revlist, width=HBwindwidth)
		#mc.button(label = "svnadd", align="center", command = "svntools.svnadd()", width=HBwindwidth)
		#mc.button(label = "svncommit", align="center", command = "svntools.svncommit()", width=HBwindwidth)
		#mc.button(label = "svninfo", align="center", command = "svntools.svninfo()", width=HBwindwidth)
		mc.button(label = "svndiscard", align="center", command = self.checkout.discard, width=HBwindwidth)
		mc.button(label = "Config", align="center", command = self.checkout.cfgwin, width=HBwindwidth)
		mc.button(label = "Quit", align="center", command = "mc.deleteUI(\"" + HBmainwin + "\")", width=HBwindwidth)
		mc.showWindow(HBmainwin)
		mc.window(HBmainwin, edit = True, height = HBwindheight, width = HBwindwidth)
	
def svnmain():
	print "svnmain()"
	global HBmainwin, myrepos
	myrepos = repos()
	mycheckout = checkedout(myrepos)
	mymainwindow = mainwindow(mycheckout)

def svnadd():
	print "svnadd()"
	if svnsave():
		HBclient = pysvn.Client()
		dironly = re.compile('/[^/]*$')
		HBdirname = dironly.sub('', svnname())
		HBlist = HBclient.status(HBdirname)
		version_check = HBlist[len(HBlist)-1]
		if not version_check.is_versioned:
			HBclient.add(HBdirname)

def svndiscard():
	HBanswer = mc.confirmDialog(title = "Discard changes?", \
				message = "Discard all changes and reload last committed version?", \
				button = ["Yes", "No"], defaultButton = "No", cancelButton = "No", \
				dismissString = "No")
	if HBanswer == "Yes":
		print "Reverting..."
		HBclient = pysvn.Client()
		HBfilename = svnname()
		#HBclient.unlock(HBfilename)
		HBclient.revert(HBfilename)
		if (mc.file(HBfilename, open = True, force = True)):
			return 1
		else:
			return 0
	else:
		print "Cancelled"
		return 0

def svnsave():
	print "svnsave()"
	HBsavename = svnname()

	if not os.access(HBsavename, os.W_OK):
		print HBsavename
		dironly = re.compile('/[^/]*$')
		HBdirname = dironly.sub('', HBsavename)
		print HBdirname
		os.makedirs(HBdirname)

	mc.file(rename = svnname())
	if mc.file(save = True, type = 'mayaAscii'):
		return 1
	else:
		return 0
	
def svncommit():
	print "svncommit()"
	if svnsave():
		HBclient = pysvn.Client()
		HBsavename = svnname()
		dironly = re.compile('/[^/]*$')
		HBdirname = dironly.sub('', HBsavename)
		HBclient.checkin([HBdirname, HBsavename], 'another test commit message, still hardcoded')

def svninfo():
	print "svninfo()"
	HBclient = pysvn.Client()
	HBheadrev = pysvn.Revision(pysvn.opt_revision_kind.head)
	HBcurrrev = HBheadrev
	HBalllogs = HBclient.log(svnname())
	HBlistwin = mc.window()
	HBwindwidth=600
	HBwindheight=300
	mc.window(HBlistwin, edit = True, widthHeight = [HBwindwidth, HBwindheight])
	HBcolumns = mc.columnLayout(columnAttach = ('both', 5), columnWidth = HBwindwidth)
	HBrevlist = []
	HBcount = 0
	for HBentrydict in HBalllogs:
		HBstring="Revision %d by %s - %s" % (HBentrydict['revision'].number, HBentrydict['author'], HBentrydict['message'])
		print HBstring
		HBrevlist.append(HBstring)
		HBcount = HBcount + 1

	#HBlistbox = mc.textScrollList(numberOfRows = HBcount, append = HBrevlist)
	#mc.button()
	mc.showWindow(HBlistwin)

if __name__ == "svntools":
	svnmain()
