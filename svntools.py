import maya.cmds as mc
import os, re, pickle, string as str
import pysvn, time

class checkedout:
	"This class holds details of the local version of a file"
	def __init__(self):
		self.repos = repos()
		self.client = pysvn.Client()
		self.assetname = "jonboy"
		self.projectname = "monkeyproject"
		self.tempdir = "/cgstaff/hbush/svntemp/"
		
		if mc.optionVar(exists = 'svnProtocol'):
			self.readcfg()
	
	def localdir(self):
		return self.tempdir + self.projectname

	def filename(self):
		return self.localdir() + '/' + self.assetname + '/' + self.projectname + '.' + self.assetname + '.ma'

	def readcfg(self):
		self.repos.name = mc.optionVar(q = 'svnReposName')
		self.repos.dir = mc.optionVar(q = 'svnReposDir')
		self.repos.hostname = mc.optionVar(q = 'svnHostName')
		self.repos.protocol = mc.optionVar(q = 'svnProtocol')
		self.tempdir = mc.optionVar(q = 'svnTempDir')
		self.projectname = mc.optionVar(q = 'svnProjName')
		self.assetname = mc.optionVar(q = 'svnAssetName')

	def writecfg(self):
		mc.optionVar(sv = [('svnReposName', self.repos.name), ('svnReposDir', self.repos.dir), ('svnHostName', self.repos.hostname), ('svnProtocol', self.repos.protocol)])
		mc.optionVar(sv = [('svnTempDir', self.tempdir), ('svnProjName', self.projectname), ('svnAssetName', self.assetname)])

	def revlist(self, what):
		HBheadrev = pysvn.Revision(pysvn.opt_revision_kind.head)
		HBcurrrev = HBheadrev
		HBalllogs = self.client.log(self.filename())
		if mc.window("svnToolsRevListWin", exists = True):
			mc.deleteUI("svnToolsRevListWin")
		self.listwin = mc.window("svnToolsRevListWin")
		HBwindwidth=600
		HBwindheight=600
		mc.window(self.listwin, edit = True, widthHeight = [HBwindwidth, HBwindheight], title = "Select a revision to check out")
		HBcolumns = mc.columnLayout(columnAttach = ('both', 5), adj = True)
		HBrevlist = []
		HBcount = 0
		for HBentrydict in HBalllogs:
			HBstring="Revision %d by %s - %s" % (HBentrydict['revision'].number, HBentrydict['author'], HBentrydict['message'])
			HBrevlist.append(HBstring)
			HBcount = HBcount + 1
		self.revlistbox = mc.textScrollList(numberOfRows = HBcount, append = HBrevlist, height = HBwindheight - 50)
		HBgrids = mc.rowLayout (nc = 2, columnWidth2 = [HBwindwidth/2,HBwindwidth/2], columnAttach2 = (["right", "left"]), width = HBwindwidth)
		mc.button(label = "OK", command = self.revlistcall, width = 100, align = "center")
		mc.button(label = "Cancel", command = self.revlistclose, width = 100, align = "center")
		mc.showWindow(self.listwin)
		mc.window(self.listwin, edit = True, height = HBwindheight, width = HBwindwidth)

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
		if not os.path.exists(self.localdir()):
			os.makedirs(self.localdir())
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
			if not self.client.info(self.localdir()).url == self.repos.url():
				print "Switching..."
				rmrec(self.localdir())
		else:
			print "File not currently under version control"
		if os.path.isfile(HBfilename):
			os.remove(HBfilename)
		if revnum != 0:
			print "Checking out revision number %d" % revnum
			HBrev = pysvn.Revision(pysvn.opt_revision_kind.number, revnum)
			self.client.checkout(self.repos.url(), self.localdir(), revision = HBrev)
		else:
			print "Checking out youngest revision"
			self.client.checkout(self.repos.url(), self.localdir())
		mc.file(self.filename(), o = True, force = True)
			
	def discard(self, ignored):
		HBfilename=self.filename()
		HBanswer = mc.confirmDialog(title = "Discard changes?", \
					message = "Discard all changes and revert to the last checked out version?", \
					button = ["Yes", "No"], defaultButton = "No", cancelButton = "No", \
					dismissString = "No")
		if HBanswer == "Yes":
			print "Reverting..."
			HBfilename = self.filename()
			self.client.revert(HBfilename)
			if (mc.file(HBfilename, open = True, force = True)):
				return 1
			else:
				return 0
		else:
			print "Cancelled"
			return 0

	def save(self):
		HBsavename = self.filename()

		if not os.access(HBsavename, os.W_OK):
			dironly = re.compile('/[^/]*$')
			HBdirname = dironly.sub('', HBsavename)
			os.makedirs(HBdirname)

		mc.file(rename = HBsavename)
		if mc.file(save = True, type = 'mayaAscii'):
			return 1
		else:
			return 0
		
	def commit(self, ignored):
		if self.save():
			HBsavename = self.filename()
			dironly = re.compile('/[^/]*$')
			HBresult = mc.promptDialog(title = "Enter commit message",\
					message = "Please enter a description of the edits you are committing", button = ['OK', 'Cancel'],\
					defaultButton = 'OK', cancelButton = 'Cancel', dismissString = 'Cancel')
			if HBresult == 'OK':
				HBcommitmessage = mc.promptDialog(q = True, text = True)
			else:
				return 0

			HBdirname = dironly.sub('', HBsavename)
			if self.client.checkin([HBdirname, HBsavename], HBcommitmessage):
				mc.headsUpMessage("Commit successful")
			else:
				promptMessage = "The commit was unsuccessful.\n Make sure you save a copy of your edited file to a\ndifferent folder, then tell your system administrator"
				HBresult = mc.confirmDialog(title = "Commit failed",\
					message = promptMessage, button = 'OK',\
					defaultButton = 'OK', cancelButton = 'OK', dismissString = 'OK')
				



	def add(self):
		if self.save():
			dironly = re.compile('/[^/]*$')
			HBdirname = dironly.sub('', svnname())
			HBlist = self.client.status(HBdirname)
			version_check = HBlist[len(HBlist)-1]
			if not version_check.is_versioned:
				self.client.add(HBdirname)

class repos:
	"All the details for a repository are stored in here"
	def __init__(self):
		self.protocol = "svn+ssh"
		self.hostname = "wg09henry"
		self.dir = "/cgstaff/hbush/.repos/"
		self.name = "svntest"

	def url(self):
		return self.protocol + "://" + self.hostname + self.dir + self.name

	def projexists(self, testproj):
		HBclient = pysvn.Client()
		allprojs = HBclient.list(self.url())
		for eachproj in allprojs:
			print eachproj

class configwin:
	"Creates a config window"
	def __init__(self, mycheckout):
		self.checkout = mycheckout
		self.repos = mycheckout.repos
		if mc.window("svnToolsConfigWin", exists = True):
			mc.deleteUI("svnToolsConfigWin")
		self.winref = mc.window("svnToolsConfigWin")
		HBwindwidth=600
		HBwindheight=320
		mc.window(self.winref, edit = True, height = HBwindheight, width = HBwindwidth, title = "SVN Tools Config")

		topLevel = mc.columnLayout(adjustableColumn = True)
		HBtabs = mc.tabLayout()

		self.reposTab(HBtabs)
		self.localTab(HBtabs)

		mc.setParent(topLevel)
		closeBut = mc.button(label = "Close", command = self.close)

		mc.showWindow(self.winref)
		mc.window(self.winref, edit = True, height = HBwindheight, width = HBwindwidth)

	def reposTab(self, parent):
		HBcolumns = mc.columnLayout(adjustableColumn = True)
		mc.tabLayout(parent, edit = True, tabLabel = (HBcolumns, "Repository"))
		self.urldisplay = mc.text (label = self.repos.url(), align = "center")
		
		HBgrids = mc.gridLayout (numberOfColumns = 2, cellWidthHeight=(300, 120))
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

		mc.setParent(parent)

	def localTab(self, parent):
		HBcolumns = mc.columnLayout(adjustableColumn = True)
		mc.tabLayout(parent, edit = True, tabLabel = (HBcolumns, "Local Copy"))
		self.filenamedisplay = mc.text (label = self.checkout.filename(), align = "center")

		HBgrids = mc.gridLayout (numberOfColumns = 2, cellWidthHeight=(300, 120))

		mc.frameLayout(label = "Project name")
		self.projnamefield = mc.textField(editable = True, text = self.checkout.projectname)
		mc.textField(self.projnamefield, edit = True, cc = self.changeproj)

		mc.setParent(HBgrids)
		mc.frameLayout(label = "Asset name")
		self.assnamefield = mc.textField(editable = True, text = self.checkout.assetname)
		mc.textField(self.assnamefield, edit = True, cc = self.changeass)

		mc.setParent(HBgrids)
		mc.frameLayout(label = "Temporary directory")
		self.tempdirfield = mc.textField(editable = True, text = self.checkout.tempdir)
		mc.textField(self.tempdirfield, edit = True, cc = self.changetemp)

		mc.setParent(parent)

	def changetemp(self, newname):
		if newname[len(newname)-1] != '/':
			newname = newname + '/'
		self.checkout.tempdir = newname
		self.somethingchanged()

	def changeproj(self, newname):
		self.checkout.repos.projexists(newname)
		self.checkout.projectname = newname
		self.somethingchanged()

	def changeass(self, newname):
		self.checkout.assetname = newname
		self.somethingchanged()

	def changereposname(self, newname):
		self.repos.name = newname
		self.somethingchanged()

	def changereposdir(self, newdir):
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
		self.updatewin()
		self.checkout.writecfg()

	def updatewin(self):
		mc.text(self.urldisplay, edit = True, label = self.repos.url())
		mc.text(self.filenamedisplay, edit = True, label = self.checkout.filename())

	def close(self, ignored):
		mc.deleteUI(self.winref)

class mainwindow:
	"Creates the main window"
	def __init__(self, passedcheckout):
		HBwindwidth = 300
		HBwindheight = 500
		self.checkout = passedcheckout
		if mc.window("svnToolsMainWin", exists = True):
			mc.deleteUI("svnToolsMainWin")
		HBmainwin = mc.window("svnToolsMainWin")
		mc.window(HBmainwin, edit = True, height = HBwindheight, width = HBwindwidth, title = "SVN Tools for Maya")
		HBcolumns = mc.columnLayout(adjustableColumn = True)
		mc.button(label = "Checkout youngest version", align="center", command = self.checkout.coyoung, width=HBwindwidth)
		mc.button(label = "Checkout older version", align="center", command = self.checkout.revlist, width=HBwindwidth)
		#mc.button(label = "svnadd", align="center", command = "svntools.svnadd()", width=HBwindwidth)
		mc.button(label = "Commit changes", align="center", command = self.checkout.commit, width=HBwindwidth)
		mc.button(label = "Discard changes", align="center", command = self.checkout.discard, width=HBwindwidth)
		mc.button(label = "Config", align="center", command = self.checkout.cfgwin, width=HBwindwidth)
		mc.button(label = "Quit", align="center", command = "mc.deleteUI(\"" + HBmainwin + "\")", width=HBwindwidth)
		mc.showWindow(HBmainwin)
		mc.window(HBmainwin, edit = True, height = HBwindheight, width = HBwindwidth)
	
def svnmain():
	print "svnmain()"
	mycheckout = checkedout()
	mymainwindow = mainwindow(mycheckout)

def rmrec(dirname):
	if not os.path.isdir(dirname):
		return 0
	if not os.access(dirname, os.W_OK):
		return 0
	for root, dirs, files in os.walk(dirname, topdown = False):
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

if __name__ == "svntools":
	svnmain()