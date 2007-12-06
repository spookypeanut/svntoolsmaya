import maya.cmds as mc
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import os, re, string as str
import pysvn

current = "" 

class checkedout:
	"This class holds details of the local version of a file"
	def __init__(self):
		self.repos = repos()
		self.client = pysvn.Client()
		self.assetname = "jonboy"
		self.projname = "monkeyproject"
		self.localdir = "/cgstaff/hbush/svntemp/"
		
		if mc.optionVar(exists = 'svnProtocol'):
			self.readcfg()
	
	def filename(self):
		return self.projname + '/' + self.assetname + '/' + self.projname + '.' + self.assetname + '.ma'

	def locfilename(self):
		return self.localdir + '/' + self.filename()

	def reposfilename(self):
		return self.repos.url() + '/' + self.filename()

	def readcfg(self):
		self.repos.name = mc.optionVar(q = 'svnReposName')
		self.repos.dir = mc.optionVar(q = 'svnReposDir')
		self.repos.hostname = mc.optionVar(q = 'svnHostName')
		self.repos.protocol = mc.optionVar(q = 'svnProtocol')
		self.localdir = mc.optionVar(q = 'svnTempDir')
		self.projname = mc.optionVar(q = 'svnProjName')
		self.assetname = mc.optionVar(q = 'svnAssetName')

	def writecfg(self):
		mc.optionVar(sv = [('svnReposName', self.repos.name), ('svnReposDir', self.repos.dir), ('svnHostName', self.repos.hostname), ('svnProtocol', self.repos.protocol)])
		mc.optionVar(sv = [('svnTempDir', self.localdir), ('svnProjName', self.projname), ('svnAssetName', self.assetname)])

	def revlist(self, ignored = "nothing"):
		HBheadrev = pysvn.Revision(pysvn.opt_revision_kind.head)
		HBcurrrev = HBheadrev
		HBalllogs = self.client.log(self.locfilename())
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

	def coyoung(self, ignored = "nothing"):
		self.checkout(0)

	def cfgwin(self, ignored = "nothing"):
		self.cfgwin = configwin(self)
	
	def checkout(self, revnum = 0):
		HBfilename = self.locfilename()
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
			if not self.client.info(self.localdir).url == self.repos.url():
				print "Switching..."
				rmrec(self.localdir)
		else:
			print "File not currently under version control"
		if os.path.isfile(HBfilename):
			os.remove(HBfilename)
		print "Checking out revision number %d" % revnum
		fullpath = dironly(self.locfilename())
		if not isversioned(fullpath):
			for i in ['/', (self.projname + '/'), (self.projname + '/' + self.assetname + '/')]:
				if not isversioned(self.localdir + '/' + i):
					self.client.checkout(self.repos.url() + '/' + i, self.localdir + '/' + i, recurse=False)
		if revnum != 0:
			HBrev = pysvn.Revision(pysvn.opt_revision_kind.number, revnum)
			self.client.checkout(dironly(self.reposfilename()), fullpath, revision = HBrev)
		else:
			self.client.checkout(dironly(self.reposfilename()), fullpath)

		mc.file(self.locfilename(), o = True, force = True)
			
	def adddir(self, fullpath):
		if not os.path.exists(fullpath):
			os.makedirs(fullpath)
		self.client.add(fullpath)

	def discard(self, ignored = "nothing"):
		HBfilename=self.locfilename()
		HBanswer = mc.confirmDialog(title = "Discard changes?", \
					message = "Discard all changes and revert to the last checked out version?", \
					button = ["Yes", "No"], defaultButton = "No", cancelButton = "No", \
					dismissString = "No")
		if HBanswer == "Yes":
			print "Reverting..."
			HBfilename = self.locfilename()
			self.client.revert(HBfilename)
			if (mc.file(HBfilename, open = True, force = True)):
				return 1
			else:
				return 0
		else:
			print "Cancelled"
			return 0

	def save(self):
		HBsavename = self.locfilename()
		HBdirname = dironly(HBsavename)
		if not os.access(HBdirname, os.W_OK):
			os.makedirs(HBdirname)

		mc.file(rename = HBsavename)
		if mc.file(save = True, type = 'mayaAscii'):
			return 1
		else:
			return 0
		
	def commit(self, ignored="nothing", message=""):
		if self.save():
			HBsavename = self.locfilename()
			if message == "":
				HBresult = mc.promptDialog(title = "Enter commit message",\
					message = "Please enter a description of the edits you are committing", button = ['OK', 'Cancel'],\
					defaultButton = 'OK', cancelButton = 'Cancel', dismissString = 'Cancel')
				if HBresult == 'OK':
					HBcommitmessage = mc.promptDialog(q = True, text = True)
				else:
					return 0
			else:
				HBcommitmessage = message

			HBdirname = dironly(HBsavename)
			if self.client.checkin([HBdirname, HBsavename], HBcommitmessage):
				mc.headsUpMessage("Commit successful")
			else:
				promptMessage = "The commit was unsuccessful.\nMake sure you save a copy of your edited file to a\ndifferent folder, then tell your system administrator"
				HBresult = mc.confirmDialog(title = "Commit failed",\
					message = promptMessage, button = 'OK',\
					defaultButton = 'OK', cancelButton = 'OK', dismissString = 'OK')

	def addproj(self, ignored = "monkey"):
		HBdirname = self.localdir + '/' + self.projname
		print "Adding " + HBdirname
		self.adddir(HBdirname)
		if self.client.checkin([HBdirname], 'AUTO: Adding \"%s\" project' % self.projname):
			mc.headsUpMessage("Commited new project")

	def add(self, ignored = "monkey"):
		HBdirname = self.locfilename()
		print "Adding " + self.locfilename()
		if self.save():
			print "Saved OK..."
			self.adddir(dironly(self.locfilename()))
			print self.client.status(HBdirname)
			HBlist = self.client.status(HBdirname)
			version_check = HBlist[0]
# WARNING: TODO: FIXME: this line ^^^ may not work every time. It confuses me
			print version_check
			if not version_check.is_versioned:
				print "Add succeeded"
				self.client.add(HBdirname)
			self.commit(message = "AUTO: Adding \"%s\" asset" % (self.projname + '/' +self.assetname) )

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
		allprojs = allprojs [1:]
		for eachprojdict in allprojs:
			eachproj = fileonly(eachprojdict[0]["path"])
			if eachproj == testproj:
				return 1
		return 0

	def assexists(self, projname, assname):
		HBclient = pysvn.Client()
		allprojs = HBclient.list(self.url() + "/" + projname)
		allprojs = allprojs [1:]
		for eachprojdict in allprojs:
			eachproj = fileonly(eachprojdict[0]["path"])
			if eachproj == assname:
				return 1
		return 0
		
class configwin:
	"Creates a config window"
	def __init__(self, passedco):
		self.checkout = passedco
		self.repos = passedco.repos
		if mc.window("svnToolsConfigWin", exists = True):
			mc.deleteUI("svnToolsConfigWin")
		self.winref = mc.window("svnToolsConfigWin")
		self.width = 600
		self.height = 320
		mc.window(self.winref, edit = True, height = self.height, width = self.width, title = "SVN Tools Config")

		topLevel = mc.columnLayout(adjustableColumn = True)
		HBtabs = mc.tabLayout()

		self.assetTab(HBtabs)
		self.reposTab(HBtabs)
		self.miscTab(HBtabs)

		protcontrol = {
			'svn+ssh': self.protssh,
			'svn': self.protsvn,
			'http': self.prothttp,
			'https': self.prothttps
		}[passedco.repos.protocol]
		mc.radioCollection(self.protfield, edit = True, select = protcontrol)

		mc.setParent(topLevel)
		closeBut = mc.button(label = "Close", command = self.close)

		mc.showWindow(self.winref)
		mc.window(self.winref, edit = True, height = self.height, width = self.width)

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

	def assetTab(self, parent):
		HBcolumns = mc.columnLayout(adjustableColumn = True)
		mc.tabLayout(parent, edit = True, tabLabel = (HBcolumns, "Asset"))
		self.assfilenamedisplay = mc.text (label = self.checkout.locfilename(), align = "center")

		HBgrids = mc.gridLayout (numberOfColumns = 2, cellWidthHeight=(300, 200))

		mc.frameLayout(label = "Project name")
		rawlist = self.checkout.client.list(self.checkout.repos.url())
		rawlist = rawlist[1:]
		projlist = []
		for eachproj in rawlist:
			projlist.append(fileonly(eachproj[0]["path"]))
		self.projlistbox = mc.textScrollList( append = projlist, selectCommand = self.changeproj, selectItem = self.checkout.projname)

		mc.setParent(HBgrids)
		mc.frameLayout(label = "Asset name")
		self.asslistbox = mc.textScrollList()
		self.updateasslist()

		mc.setParent(HBcolumns)
		HBgrids = mc.gridLayout (numberOfColumns = 2, cellWidthHeight=(300, 40))
		mc.button(label = "Add New Project", align="center", command=self.addnewproj)
		mc.button(label = "Add As New Asset", align="center", command=self.addnewasset)

		mc.setParent(parent)

	def miscTab(self, parent):
		HBcolumns = mc.columnLayout(adjustableColumn = True)
		mc.tabLayout(parent, edit = True, tabLabel = (HBcolumns, "Miscellaneous"))
		self.miscfilenamedisplay = mc.text (label = self.checkout.locfilename(), align = "center")

		HBgrids = mc.gridLayout (numberOfColumns = 2, cellWidthHeight=(300, 240))
		mc.setParent(HBgrids)
		mc.frameLayout(label = "Local directory")
		self.localdirfield = mc.textField(editable = True, text = self.checkout.localdir)
		mc.textField(self.localdirfield, edit = True, cc = self.changelocdir)

		mc.setParent(parent)

	def updateasslist(self):
		print "Updating asset list: switching to " + self.checkout.projname
		mc.textScrollList(self.asslistbox, edit = True, ra = True)
		rawlist = self.checkout.client.list(self.checkout.repos.url() + "/" + self.checkout.projname)
		rawlist = rawlist[1:]
		asslist = []
		for eachass in rawlist:
			asslist.append(fileonly(eachass[0]["path"]))
		if len(asslist) == 0:
			HBresult = mc.promptDialog(title = "Enter asset name",\
					message = "The project you have chosen contains no assets\nPlease enter the name of the first asset now\nThis will be committed to the repository", button = ['OK', 'Cancel'],\
					defaultButton = 'OK', cancelButton = 'Cancel', dismissString = 'Cancel')
			if HBresult == 'OK':
				newassname = mc.promptDialog(q = True, text = True)
				self.checkout.assetname = newassname
				self.checkout.add()
				asslist.append(newassname)
			else:
				return 0
		if self.checkout.assetname in asslist:
			mc.textScrollList(self.asslistbox, edit = True, append = asslist, selectItem = self.checkout.assetname, selectCommand = self.changeass)
		else:
			mc.textScrollList(self.asslistbox, edit = True, append = asslist, sii = 1, selectCommand = self.changeass)

	def addnewproj(self, ignored = "monkey"):
		HBresult = mc.promptDialog(title = "Enter new project name",\
				message = "Please enter the name of the new project", button = ['OK', 'Cancel'],\
				defaultButton = 'OK', cancelButton = 'Cancel', dismissString = 'Cancel')
		if HBresult == 'OK':
			newname = mc.promptDialog(q = True, text = True)
			self.checkout.projname = newname
			self.checkout.addproj(newname)
			self.updateasslist()

	def addnewasset(self, ignored = "monkey"):
		HBresult = mc.promptDialog(title = "Enter new asset name",\
				message = "Please enter the name of the new asset", button = ['OK', 'Cancel'],\
				defaultButton = 'OK', cancelButton = 'Cancel', dismissString = 'Cancel')
		if HBresult == 'OK':
			newname = mc.promptDialog(q = True, text = True)
			self.checkout.assetname = newname
			self.checkout.add(newname)
			self.updateasslist()
		else:
			return 0

	def changelocdir(self, newname):
		if newname[len(newname)-1] == '/':
			newname = newname[0:-1]
		self.checkout.localdir = newname
		self.somethingchanged()

	def changeproj(self):
		newname = mc.textScrollList(self.projlistbox, q = True, selectItem = True)[0]
		self.checkout.projname = newname
		self.updateasslist()
		self.somethingchanged()

	def changeass(self):
		newname = mc.textScrollList(self.asslistbox, q = True, selectItem = True)[0]
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
		mc.text(self.assfilenamedisplay, edit = True, label = self.checkout.locfilename())
		mc.text(self.miscfilenamedisplay, edit = True, label = self.checkout.locfilename())

	def close(self, ignored = "nothing"):
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
	
def initializePlugin(argument = "monkey"):
	global current
	current = checkedout()
	mymainwindow = mainwindow(current)
	print "SVN Tools plug-in loaded"
	print argument

def uninitializePlugin(argument = "monkey"):
	print "SVN Tools plug-in unloaded"
	print argument

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
	print "Checking whether " + checkfile + " is versioned..."
	HBclient = pysvn.Client()
	HBdirname = dironly(checkfile)
	if not os.path.exists(HBdirname + ".svn"):
		print HBdirname + ".svn doesn't exist: assuming unversioned"
		return 0
	return HBclient.status(checkfile)[0].is_versioned

def dironly(fullpath):
	dironlyre = re.compile('/[^/]*$')
	return dironlyre.sub('/', fullpath)

def fileonly(fullpath):
	fileonlyre = re.compile('^.*\/')
	return fileonlyre.sub('', fullpath)

if __name__ == "svntools":
	initializePlugin()
