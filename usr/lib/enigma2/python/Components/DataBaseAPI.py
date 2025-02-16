from bisect import bisect_left, insort
from ctypes import py_object, pythonapi, c_long
from difflib import SequenceMatcher
from gettext import gettext as _
from os import remove, stat, walk, mknod
from os.path import exists, dirname, realpath, isdir, join, basename, split
from sqlite3 import connect, ProgrammingError, OperationalError, DatabaseError
from struct import unpack
from threading import Thread, Lock, current_thread
from time import sleep, time
from enigma import eServiceCenter, eServiceReference, iServiceInformation, eTimer
from Components.Task import Task, Job, job_manager
from Components.config import config, ConfigDirectory, ConfigYesNo
from Components.FunctionTimer import functionTimer
from Screens.MessageBox import MessageBox
from Tools.Notifications import AddPopup
from Tools.MovieInfoParser import getExtendedMovieDescription
from Tools.CoreUtils import getUniqueID

BASEINIT = None
has_e2 = True
lock = Lock()


config.misc.db_path = ConfigDirectory(default="/media/hdd/")
config.misc.db_enabled = ConfigYesNo(default=True)


class LOGLEVEL:
	OFF = 5
	ERROR = 4
	WARN = 3
	INFO = 2
	ALL = 1

	def __init__(self):
		self.LogFile = self.createLogFile()

	def createLogFile(self):
		db_path = config.misc.db_path.value
		if not db_path.endswith("/"):
			db_path += "/"
		if not exists(db_path):
			db_path = "/media/hdd/"
		return f"{db_path}db_error.log"


loglevel = LOGLEVEL()


def debugPrint(str, level=0):
	cur_level = loglevel.INFO
	if level >= cur_level:
		print("[DataBase] " + str)
	if level >= loglevel.ERROR:
		print("[DataBase] " + str)


def prepareStringIN(txt):
#	ret = ""
#	try:
#		ret = txt.decode("utf-8")
#	except UnicodeDecodeError:
#		ret = unicode(txt, "ISO-8859-1")
	return txt


class globalThreads():

	def __init__(self):
		self.registered_threads = []

	def terminate_thread(self, mythread):
		if not mythread.isAlive():
			return
		exc = py_object(SystemExit)
		res = pythonapi.PyThreadState_SetAsyncExc(c_long(mythread.ident), exc)
		if res == 0:
			print("[DataBaseAPI] can not kill list update")
		elif res > 1:
			pythonapi.PyThreadState_SetAsyncExc(mythread.ident, None)
			print("[DataBaseAPI] can not terminate list update")
		elif res == 1:
			print("[DataBaseAPI] successfully terminate thread")
		del exc
		del res
		return 0

	def registerThread(self, mythread):
		if mythread not in self.registered_threads:
			self.registered_threads.append(mythread)

	def unregisterThread(self, mythread):
		if mythread in self.registered_threads:
			self.registered_threads.remove(mythread)

	def shutDown(self):
		for t in self.registered_threads:
			self.terminate_thread(t)


globalthreads = globalThreads()


class databaseJob(Job):
	def __init__(self, fnc, args, title):
		Job.__init__(self, title)
		self.database_job = databaseTask(self, fnc, args, title)

	def abort(self):
		self.database_job.abort()

	def stop(self):
		self.database_job.stop()


class databaseTask(Task):
	def __init__(self, job, fnc, args, title=""):
		Task.__init__(self, job, "")
		self.dbthread = Thread(target=fnc, args=args[1])
		self.stop_fnc = args[0]
		self.end = 100
		self.name = title
		self.msgtxt = _("Database update was finished")

	def prepare(self):
		self.error = None

	def run(self, callback):
		self.callback = callback
		self.dbthread.start()

	def stop(self):
		Task.processFinished(self, 0)
		self.stop_fnc()
		debugPrint("job finished", LOGLEVEL.INFO)
#		from Screens.Standby import inStandby
#		if not inStandby:
#			AddPopup(text = self.msgtxt, type = MessageBox.TYPE_INFO, timeout = 20, id = "db_update_stopped")

	def abort(self):
		self.msgtxt = _("Database update was cancelled")
		debugPrint("job cancelled", LOGLEVEL.INFO)
		self.stop()


class DatabaseState(object):
	def __init__(self, dbfile, boxid):
		self.lockfile = dbfile + ".lock"
		self.boxid = boxid
		self.lockFileCleanUp()
		self.check_remote_lock = False
		self.available_stbs = []
		global BASEINIT
		if BASEINIT is None:
			BASEINIT = True
			self.unlockDB()

	def lockFileCleanUp(self):
		content = ""
		if exists(self.lockfile):
			try:
				with open(self.lockfile, "r") as f:
					content = f.readlines()
			except OSError as e:
				pass
			if content and len(content) >= 1:
				lockid = content[0]
				if lockid.startswith(self.boxid):
					try:
						remove(self.lockfile)
					except OSError as e:
							pass

	def isRemoteLocked(self):
		ret = False
		if not self.check_remote_lock:
			return ret
		max_recursion = 5
		for i in range(0, max_recursion):
			lockid = ""
			ret = False
			if exists(self.lockfile):
				try:
					with open(self.lockfile, "r") as f:
						content = f.readlines()
				except OSError as e:
					break
				if content and len(content) >= 1:
					lockid = content[0]
					if not lockid.startswith(self.boxid):
						if lockid in self.available_stbs or len(self.available_stbs) <= 0:
							if i >= max_recursion - 1:
								#txt = _("The database is currently used by another Vu+ STB, please try again later")
								#AddPopup(text = txt, type = MessageBox.TYPE_INFO, timeout = 20, id = "db_locked")
								ret = True
							else:
								sleep(0.1)
						else:
							try:
								remove(self.lockfile)
							except OSError as e:
								pass
							break
					else:
						break
				else:
					try:
						remove(self.lockfile)
					except OSError as e:
						pass
					break
			else:
				break
		return ret

	def lockDB(self):
		if not self.check_remote_lock:
			return
		try:
			with open(self.lockfile, "w") as f:
				f.write(self.boxid)
		except OSError as e:
			pass

	def unlockDB(self):
		if self.check_remote_lock and not self.isRemoteLocked():
			try:
				remove(self.lockfile)
			except OSError as e:
				pass


class CommonDataBase():
	def __init__(self, db_file=None):
		db_path = config.misc.db_path.value
		if not db_path.endswith("/"):
			db_path += "/"
		if not exists(db_path):
			db_path = "/media/hdd/"
		self.db_file = db_path + "moviedb.db" if not db_file else db_path + db_file
		self.boxid = getUniqueID("e" + "t" + "h" + "0")
		self.dbstate = DatabaseState(self.db_file, self.boxid)
		debugPrint(f"init database: {self.db_file}", LOGLEVEL.INFO)
		self.c = None
		self.table = None
		self.locked = False
		self.table_structure = None
		self.dbthread_kill = False
		self.dbthread_running = False
		self.dbthread_name = _("Update Database")
		self.dbthread_id = None
		self.is_initiated = False
		self.ignore_thread_check = False
		self.db = None

	def doInit(self):
		pass

	def connectDataBase(self, readonly=False):
		if not config.misc.db_enabled.value:
			return False
		if not self.is_initiated:
			self.doInit()
		if not self.ignore_thread_check and self.dbthread_id is not None and not readonly:
			cur_id = current_thread().ident
			if cur_id != self.dbthread_id:
				debugPrint("connecting failed --> THREAD error! another thread is using the database", LOGLEVEL.ERROR)
				return False
		if self.locked and not readonly:
			debugPrint("connecting failed --> database locked !", LOGLEVEL.ERROR)
			return False
		if not self.c:
			if self.dbstate.isRemoteLocked():
				if len(self.dbstate.available_stbs):
					return False
			else:
				self.dbstate.lockDB()
			debugPrint(f"connect table {self.table} of database: {self.db_file}", LOGLEVEL.ALL)
			db_dir = dirname(self.db_file)
			if not exists(db_dir):
				debugPrint(f"connect table failed --> {db_dir} does not exist", LOGLEVEL.ERROR)
				return False
			chk_same_thread = not self.ignore_thread_check and True or False
			self.db = connect(self.db_file, check_same_thread=chk_same_thread)
			self.c = self.db.cursor()
			sqlcmd = "PRAGMA case_sensitive_like=ON;"
			self.executeSQL(sqlcmd, readonly=True)
		if self.c and self.table is not None:
			return True
		return False

	def commitDB(self):
		txt = ""
		if not hasattr(self, "db"):
			txt = "not opened --> skip committing"
			debugPrint(txt, LOGLEVEL.ERROR)
		hasError = True
		try:
			lock.acquire(True)
			if self.db:
				self.db.commit()
			hasError = False
		except ProgrammingError as errmsg:
			txt = _("ERROR at committing database changes: ProgrammingError")
		except OperationalError as errmsg:
			txt = _("ERROR at committing database changes: OperationalError")
		finally:
			errmsg = ""
			lock.release()
		if hasError:
			txt += "\n"
			txt += str(errmsg)
			debugPrint(txt, LOGLEVEL.ERROR)
			txt = _("Error during committing changes")
			AddPopup(text=txt, type=MessageBox.TYPE_ERROR, timeout=0, id="db_error")
		return not hasError

	def closeDB(self):
		txt = ""
		if not hasattr(self, "db"):
			txt = "not opened --> skip  closing"
			debugPrint(txt, LOGLEVEL.ERROR)
		hasError = True
		try:
			lock.acquire(True)
			self.c = None
			if self.db:
				self.db.close()
			hasError = False
		except ProgrammingError as errmsg:
			txt = _("Programming ERROR at closing database")
		except OperationalError as errmsg:
			txt = _("Operational ERROR at closing database")
		finally:
			errmsg = ""
			lock.release()
		if hasError:
			txt += "\n"
			txt += str(errmsg)
			debugPrint(txt, LOGLEVEL.ERROR)
			txt = _("Error at closing database")
			AddPopup(text=txt, type=MessageBox.TYPE_ERROR, timeout=0, id="db_error")
		return not hasError

	def executeSQL(self, sqlcmd, args=[], readonly=False):
		if self.connectDataBase(readonly):
			ret = []
			debugPrint("SQL cmd: " + sqlcmd.encode("utf-8"), LOGLEVEL.ALL)
			txt = "\n"
			for i in args:
					txt += i.encode("utf-8") + "\n"
			debugPrint("SQL arguments: " + txt, LOGLEVEL.ALL)
			if not readonly:
				self.locked = True
			hasError = True
			try:
				lock.acquire(True)
				if self.c:
					self.c.execute(sqlcmd, args)
					ret = self.c.fetchall()
				hasError = False
			except ProgrammingError as errmsg:
				txt = f"Programming ERROR at SQL command: {sqlcmd}"
				if len(args):
					txt += "\n"
					for arg in args:
						txt += f"{arg}\n"
			except DatabaseError as errmsg:
				txt = f"Database ERROR at SQL command: {sqlcmd}"
				if len(args):
					txt += "\n"
					for arg in args:
						txt += f"{arg}\n"
				try:
					self.closeDB()
				except OSError:
					pass
				if str(errmsg).find("malformed") != -1:
					txt += "\n---> try to delete malformed database"
					try:
						remove(self.db_file)
					except OSError:
						pass
					self.is_initiated = False
			except Exception as errmsg:
				txt = f"Database ERROR at SQL command: {sqlcmd}"
			finally:
				errmsg = ""
				lock.release()
			if hasError:
				txt += "\n"
				txt += str(errmsg)
				debugPrint(txt, LOGLEVEL.ERROR)
				self.disconnectDataBase()
				txt = _("Error during database transaction")
			if not readonly:  # AddPopup(text = txt, type = MessageBox.TYPE_ERROR, timeout = 0, id = "db_error")
				self.locked = False
			return (not hasError, ret)

	def disconnectDataBase(self, readonly=False):
		if self.c is not None:
			debugPrint(f"disconnect table {self.table} of database: {self.db_file}", LOGLEVEL.ALL)
			if self.dbthread_id is not None:
				cur_id = current_thread().ident
				if cur_id != self.dbthread_id:
					debugPrint("connecting failed --> THREAD error! another thread is using the database", LOGLEVEL.ERROR)
					return False
			if not readonly:
				self.commitDB()
			self.closeDB()
			self.c = None
			self.dbstate.unlockDB()

	def doVacuum(self):
		if self.connectDataBase():
			sqlcmd = "VACUUM"
			self.executeSQL(sqlcmd)

	def createTable(self, fields):
		if self.table and self.connectDataBase():
			field_str = "("
			for name in fields:
				field_str += name + " " + fields[name] + ","
			if field_str.endswith(","):
				field_str = field_str[:-1] + ")"
			self.executeSQL("CREATE TABLE if not exists " + self.table + " " + field_str)
			self.commitDB()

	def checkTableColumns(self, fields, force_remove=False):
		if self.table and self.connectDataBase():
			struc = self.getTableStructure()
			for column in fields:
				if column not in struc:
					sqlcmd = 'ALTER TABLE ' + self.table + ' ADD COLUMN ' + column + ' ' + fields[column] + ';'
					self.executeSQL(sqlcmd)
			if force_remove:
				columns_str = ''
				for column in fields:
					columns_str += column + ' ' + fields[column] + ','
				if columns_str.endswith(','):
					columns_str = columns_str[:-1]
				b_table = self.table + '_backup'
				sqlcmd = 'CREATE TEMPORARY TABLE ' + b_table + '(' + columns_str + ');'
				self.executeSQL(sqlcmd)
				sqlcmd = 'INSERT INTO ' + b_table + ' SELECT ' + columns_str + ' FROM ' + self.table + ';'
				self.executeSQL(sqlcmd)
				sqlcmd = 'DROP TABLE ' + self.table + ';'
				self.executeSQL(sqlcmd)
				self.createTable(fields)
				sqlcmd = 'INSERT INTO ' + self.table + ' SELECT ' + columns_str + ' FROM ' + b_table + ';'
				self.executeSQL(sqlcmd)
				sqlcmd = 'DROP TABLE ' + b_table + ';'
				self.executeSQL(sqlcmd)
				self.table_structure = None
			self.commitDB()
		self.table_structure = None

	def createTableIndex(self, idx_name, fields, unique=True):
		if self.table and self.connectDataBase():
			unique_txt = 'UNIQUE'
			if not unique:
				unique_txt = ''
			idx_fields = ''
			if isinstance(fields, str):
				idx_fields = fields
			else:
				for field in fields:
					idx_fields += field + ', '
			if idx_fields.endswith(', '):
				idx_fields = idx_fields[:-2]
			sqlcmd = 'CREATE ' + unique_txt + ' INDEX IF NOT EXISTS ' + idx_name + ' ON ' + self.table + ' (' + idx_fields + ');'
			self.executeSQL(sqlcmd)

	def dropTable(self):
		if self.table and self.connectDataBase():
			self.table_structure = None
			self.executeSQL("drop table if exists " + self.table)

	def getTables(self):
		tables = []
		if self.connectDataBase():
			sqlret = self.executeSQL("SELECT name FROM sqlite_master WHERE type='table';")
			if sqlret and sqlret[0]:
				res = sqlret[1]
			else:
				return tables
			for t in res:
				debugPrint("found table: " + t[0], LOGLEVEL.ALL)
				tables.append(t[0])
		return tables

	def getTableStructure(self):
		if self.table_structure is None or not len(self.table_structure):
			structure = {}
			if self.table and self.connectDataBase():
				sqlret = self.executeSQL("PRAGMA table_info('" + self.table + "');")
				if sqlret and sqlret[0]:
					rows = sqlret[1]
				else:
					return structure
				for row in rows:
					structure[str(row[1])] = str(row[2])
				debugPrint("Data structure of table: " + self.table + "\n" + str(structure), LOGLEVEL.ALL)
			self.table_structure = structure
			if self.dbstate.check_remote_lock:
				for x in structure:
					if x.startswith('fp_'):
						r_stb = str(x.lstrip('fp_'))
						if r_stb not in self.dbstate.available_stbs:
							self.dbstate.available_stbs.append(r_stb)
		return self.table_structure

	def addColumn(self, column, c_type="TEXT"):
		if self.connectDataBase():
			struc = self.getTableStructure()
			if self.table and column not in struc:
				sqlcmd = 'ALTER TABLE ' + self.table + ' ADD COLUMN ' + column + ' ' + c_type + ';'
				self.executeSQL(sqlcmd)
				self.table_structure = None

	def getTableContent(self):
		rows = []
		content = []
		if self.table and self.connectDataBase():
			sqlret = self.executeSQL("SELECT * FROM " + self.table + ";")
			if sqlret and sqlret[0]:
				rows = sqlret[1]
			else:
				return content
			i = 1
			for row in rows:
				tmp_row = []
				for field in row:
					tmp_field = field
					if field and isinstance(field.encode('utf-8'), str):
						tmp_field = field.encode('utf-8')
					tmp_row.append(tmp_field)
				content.append(tmp_row)
				debugPrint("Found row (" + str(i) + "):" + str(tmp_row), LOGLEVEL.ALL)
				i += 1
		return content

	def searchDBContent(self, data, fields="*", query_type="AND", exactmatch=False, compareoperator=''):
		rows = []
		content = []
		if exactmatch or compareoperator in ('<', '<=', '>', '>='):
			wildcard = ''
			compare = compareoperator + ' ' if compareoperator in ('<', '<=', '>', '>=') else '='
		else:
			compare = 'LIKE '
			wildcard = '%'
		if query_type not in ("AND", "OR"):
			query_type = "AND"
		if not isinstance(data, dict):
			return content
		struc = self.getTableStructure()
		for field in data:
			if field not in struc:
				return content
		return_fields = ''
		if fields != '*':
			if (isinstance(fields, tuple) or isinstance(fields, list)) and len(fields):
				for field in fields:
					if field in struc:
						return_fields += field + ', '
			elif isinstance(fields, str):
				if fields in struc:
					return_fields = fields
		if return_fields == '':
			return_fields = '*'
		if return_fields.endswith(', '):
			return_fields = return_fields[:-2]
		if self.table and self.connectDataBase():
			sqlcmd = 'SELECT ' + return_fields + ' FROM ' + self.table + ' WHERE '
			args = []
			for key in data:
				sqlcmd += key + ' ' + compare + '? ' + query_type + ' '
				args.append(wildcard + prepareStringIN(data[key]) + wildcard)
			if sqlcmd.endswith(' ' + query_type + ' '):
				sqlcmd = sqlcmd[:-(len(query_type) + 2)] + ';'
			if not exactmatch:
				sqlpragmacmd = 'PRAGMA case_sensitive_like=OFF;'
				self.executeSQL(sqlpragmacmd, readonly=True)
			sqlret = self.executeSQL(sqlcmd, args, readonly=True)
			if not exactmatch:
				sqlpragmacmd = 'PRAGMA case_sensitive_like=ON;'
				self.executeSQL(sqlpragmacmd, readonly=True)
			if sqlret and sqlret[0]:
				rows = sqlret[1]
			else:
				return content
			self.disconnectDataBase(True)
			i = 1
			for row in rows:
				tmp_row = []
				for field in row:
					tmp_field = field
					if field and isinstance(str(field).encode('utf-8'), str):
						tmp_field = str(field).encode('utf-8')
					tmp_row.append(tmp_field)
				content.append(tmp_row)
				debugPrint("Found row (" + str(i) + "):" + str(tmp_row), LOGLEVEL.ALL)
				i += 1
		return content

	def insertRow(self, data, unique_fields=""):
		if self.connectDataBase():
			struc = self.getTableStructure()
			is_valid = True
			fields = []
			for field in data:
				if field not in struc:
					is_valid = False
					break
			if self.table and is_valid:
				args = []
				sqlcmd = 'INSERT INTO ' + self.table + '('
				for key in data:
					sqlcmd += key + ','
				if sqlcmd.endswith(','):
					sqlcmd = sqlcmd[:-1]
				sqlcmd += ') SELECT '
				for key in data:
					sqlcmd += '"' + prepareStringIN(data[key]) + '",'
				if sqlcmd.endswith(','):
					sqlcmd = sqlcmd[:-1] + ' '
				if unique_fields != "":
					if isinstance(unique_fields, str) and unique_fields in data:
						sqlcmd += 'WHERE NOT EXISTS(SELECT 1 FROM ' + self.table + ' WHERE ' + unique_fields + ' =?)'
						args = [prepareStringIN(data[unique_fields]),]
					elif isinstance(unique_fields, tuple) or isinstance(unique_fields, list):
						if len(unique_fields) == 1:
							if unique_fields[0] in data:
								sqlcmd += 'WHERE NOT EXISTS(SELECT 1 FROM ' + self.table + ' WHERE ' + unique_fields[0] + ' =?)'
								args = [prepareStringIN(data[unique_fields[0]]),]
						elif len(unique_fields) > 1:
							sql_limit = ""
							for unique_field in unique_fields:
								if unique_field in data:
									sql_limit += unique_field + ' =? AND '
									args.append(prepareStringIN(data[unique_field]))
							if sql_limit.endswith(' AND '):
								sql_limit = sql_limit[:-5]
							if sql_limit != '':
								sqlcmd += 'WHERE NOT EXISTS(SELECT 1 FROM ' + self.table + ' WHERE ' + sql_limit + ')'
				self.executeSQL(sqlcmd, args)

	def insertUniqueRow(self, data, replace=False):
		if self.table and self.connectDataBase():
			struc = self.getTableStructure()
			for field in data:
				if field not in struc:
					is_valid = False
					return
			method = 'IGNORE'
			if replace:
				method = 'REPLACE'
			args = []
			sqlcmd = 'INSERT OR ' + method + ' INTO ' + self.table + '('
			for key in data:
				sqlcmd += key + ','
				args.append(prepareStringIN(data[key]))
			if sqlcmd.endswith(','):
				sqlcmd = sqlcmd[:-1]
			sqlcmd += ') VALUES ('
			for key in data:
				sqlcmd += '?,'
			if sqlcmd.endswith(','):
				sqlcmd = sqlcmd[:-1]
			sqlcmd += ');'
			self.executeSQL(sqlcmd, args)

	def updateUniqueData(self, data, idx_fields):
		for field in idx_fields:
			if field not in data:
				return
		struc = self.getTableStructure()
		for field in data:
			if field not in struc:
				return
		self.insertUniqueRow(data, replace=False)
		if not self.c:
			return
		if self.c.rowcount > 0:
			return
		args = []
		if self.table:
			sqlcmd = 'UPDATE ' + self.table + ' SET '
			for key in data:
				sqlcmd += key + ' = ?, '
				args.append(prepareStringIN(data[key]))
			if sqlcmd.endswith(', '):
				sqlcmd = sqlcmd[:-2]
			sqlcmd += ' WHERE '
			for key in idx_fields:
				sqlcmd += key + ' = ? AND '
				args.append(prepareStringIN(data[key]))
			if sqlcmd.endswith('AND '):
				sqlcmd = sqlcmd[:-4]
			sqlcmd += ';'
			self.executeSQL(sqlcmd, args)

	def updateData(self, data, unique_fields):
		if self.table and self.connectDataBase():
			self.insertRow(data, unique_fields)
			if not self.c:
				return
			if self.c.rowcount > 0:
				return
			struc = self.getTableStructure()
			for field in data:
				if field not in struc:
					return
			if isinstance(unique_fields, tuple) or isinstance(unique_fields, list):
				for field in unique_fields:
					if field not in struc:
						return
			else:
				if unique_fields not in struc:
						return
			args = []
			sqlcmd = 'UPDATE ' + self.table + ' SET '
			for key in data:
				sqlcmd += key + '=?, '
				args.append(prepareStringIN(data[key]))
			if sqlcmd.endswith(', '):
				sqlcmd = sqlcmd[:-2]
			if unique_fields is None or unique_fields == '':
				return
			if isinstance(unique_fields, str):
				sqlcmd += ' WHERE ' + unique_fields + ' =?'
				args.append(prepareStringIN(data[unique_fields]))
			elif isinstance(unique_fields, tuple) or isinstance(unique_fields, list):
				if len(unique_fields) == 1:
					if unique_fields[0] in data:
						sqlcmd += ' WHERE ' + unique_fields[0] + ' =?'
						args.append(prepareStringIN(data[unique_fields[0]]))
				elif len(unique_fields) > 1:
					sql_limit = ""
					for unique_field in unique_fields:
						if unique_field in data:
							sql_limit += unique_field + ' =? AND '
							args.append(prepareStringIN(data[unique_field]))
					if sql_limit.endswith(' AND '):
						sql_limit = sql_limit[:-5]
					if sql_limit != '':
						sqlcmd += ' WHERE ' + sql_limit
			self.executeSQL(sqlcmd, args)

	def deleteDataSet(self, fields, exactmatch=True):
		if self.connectDataBase():
			args = []
			struc = self.getTableStructure()
			wildcard = ''
			operator = '='
			if not exactmatch:
				wildcard = '%'
				operator = ' LIKE '
			where_str = ' WHERE '
			for column in fields:
				if column not in struc:
					return
				where_str += column + operator + '? AND '
				args.append(wildcard + prepareStringIN(fields[column]) + wildcard)
			if where_str.endswith(' AND '):
				where_str = where_str[:-5] + ';'
			sqlcmd = 'DELETE FROM ' + self.table + where_str
			self.executeSQL(sqlcmd, args)

	def doActionInBackground(self, fnc, job_name, args=[]):
		if not self.dbthread_running:
			self.dbthread_running = True
			self.dbthread_kill = False
			job_manager.AddJob(databaseJob(fnc, [self.stopBackgroundAction, args], self.dbthread_name))

	def stopBackgroundAction(self):
		self.dbthread_kill = True
		if self.dbthread_running:
			jobs = len(job_manager.getPendingJobs())
			if jobs:
				joblist = job_manager.getPendingJobs()
				for job in joblist:
					if job.name == self.dbthread_name:
						job.stop()
		self.dbthread_running = False
		self.disconnectDataBase()
		self.dbthread_id = None


class MovieDataBase(CommonDataBase):

	def __init__(self):
		self.box_path = 'fp_' + getUniqueID('e' + 't' + 'h' + '0')
		self.box_lpos = 'lpos_' + getUniqueID('e' + 't' + 'h' + '0')
		db_id = ''
		db_ver = '_v0001'
		CommonDataBase.__init__(self)
		self.dbstate.check_remote_lock = True
		self.ignore_thread_check = True
		self.table = "moviedb" + db_id + db_ver
		self.fields = {'path': 'TEXT',
			self.box_path: 'TEXT',
			'fname': 'TEXT',
			'ref': 'TEXT',
			'title': 'TEXT',
			'shortDesc': 'TEXT',
			'extDesc': 'TEXT',
			'genre': 'TEXT',
			'tags': 'TEXT',
			'autotags': 'TEXT',
			'duration': 'REAL',
			'begin': 'REAL',
			'lastpos': 'REAL',
			self.box_lpos: 'REAL',
			'fsize': 'INTEGER',
			'progress': 'REAL',
			'AudioChannels': 'INTEGER',
			'ContentType': 'INTEGER',
			'AudioFormat': 'TEXT',
			'VideoFormat': 'TEXT',
			'VideoResoltuion': 'TEXT',
			'AspectRatio': 'TEXT',
			'TmdbID': 'INTEGER',
			'TvdbID': 'INTEGER',
			'CollectionID': 'INTEGER',
			'ListID': 'INTEGER',
			'IsRecording': 'INTEGER DEFAULT 0',
			'IsTrash': 'INTEGER DEFAULT 0',
			'TrashTime': 'REAL',
			'IsDir': 'INTEGER',
			'Season': 'INTEGER',
			'Episode': 'INTEGER',
		}
		self.titlelist = {}
		self.titlelist_list = []

	def doInit(self):
		if not self.dbstate.isRemoteLocked():
			self.is_initiated = True
			self.createTable(self.fields)
			self.checkTableColumns(self.fields, force_remove=False)
			self.createTableIndex('idx_fname_fsize', ('fname', 'fsize'))
			idx_name = 'idx_fname_fsize_' + getUniqueID('e' + 't' + 'h' + '0')
			self.createTableIndex(idx_name, ('fname', 'fsize', self.box_path))
			self.disconnectDataBase()

	def reInitializeDB(self):
		if exists(self.db_file):
			try:
				remove(self.db_file)
			except OSError:
				pass
		self.is_initiated = False
		self.titlelist = {}
		self.titlelist_list = []
		self.__init__()

	def BackgroundDBUpdate(self, fnc, fnc_args=[]):
		self.dbthread_name = _("Database Update")
		self.doActionInBackground(fnc, self.dbthread_name, fnc_args)

	def BackgroundDBCleanUp(self):
		self.dbthread_name = _("Database Cleanup")
		self.doActionInBackground(self.removeDeprecated, self.dbthread_name)

	def getVideoDirs(self):
		dirs = []
		for x in config.movielist.videodirs.value:
			if not exists(x):
				continue
			if not x.endswith('/'):
				x += '/'
			dirs.append((len(x), x))
		dirs.sort(reverse=True)
		video_dirs = []
		for x in dirs:
			video_dirs.append(x[1])
		return video_dirs

	def removeDeprecated(self):
		global hase_e2
		if not has_e2:
			return
		self.dbthread_id = current_thread().ident
		items = self.searchDBContent({self.box_path: ''}, (self.box_path, 'fsize'))
		this_job = None
		joblist = job_manager.getPendingJobs()
		for job in joblist:
			if job.name == self.dbthread_name and hasattr(job, 'database_job'):
				this_job = job
				break
		i = 0
		j = 0
		count = len(items)
		for item in items:
			if self.dbthread_kill:
					break
			i += 1
			if count:
				progress = int(float(i) / float(count) * 100.0)
				if this_job:
					this_job.database_job.setProgress(progress)
			delete_data = False
			if not exists(item[0]):
				delete_data = True
			else:
				if item[1] is not None and float(item[1]) != self.getFileSize(item[0]):
					delete_data = True
			if delete_data:
				self.deleteDataSet({self.box_path: item[0]})
			if j >= 100:
				self.commitDB()
				j = 0
			j += 1
		self.doVacuum()
		self.stopBackgroundAction()

	def removeSingleEntry(self, service_path):
		global hase_e2
		if not has_e2:
			return
		items = self.searchDBContent({self.box_path: service_path}, (self.box_path, 'title', 'shortDesc', 'extDesc'))
		for item in items:
			if len(item) >= 4:
				search_fields = {self.box_path: service_path}
				is_in_db = self.searchContent(search_fields, fields=("fname",), query_type="AND", exactmatch=False, skipCheckExists=True)
				if len(is_in_db):
					self.removeFromTitleList(item[1], item[2], item[3])
			self.deleteDataSet({self.box_path: item[0]})
		self.doVacuum()
		self.disconnectDataBase()

	def getFileSize(self, fpath):
		try:
			fsize = stat(fpath).st_size
		except OSError:
			fsize = -1
		return fsize

	def inTitleList(self, mytitle, shortDesc='', extDesc='', ratio_short_desc=0.95, ratio_ext_desc=0.85):
		if int(config.misc.timer_show_movie_available.value) > 1:
			if shortDesc is None:
				shortDesc = ''
			if extDesc is None:
				extDesc = ''
			if shortDesc == '' and extDesc == '':
				return 1 if mytitle in self.titlelist else None
			else:
				if mytitle in self.titlelist:
					short_descs = self.titlelist[mytitle][0]
					short_compared = False
					movie_found = False
					if shortDesc != '':
						short_compared = True
						for short_desc in short_descs:
							sequenceMatcher = SequenceMatcher(" ".__eq__, shortDesc, short_desc)
							if sequenceMatcher.ratio() > ratio_short_desc:
								movie_found = True
								break
							if short_desc == shortDesc:
								movie_found = True
								break
					if extDesc == '' and movie_found:
						return 1
					if not movie_found and short_compared:
						return None
					ext_descs = self.titlelist[mytitle][1]
					for ext_desc in ext_descs:
						sequenceMatcher = SequenceMatcher(" ".__eq__, extDesc, ext_desc)
						if sequenceMatcher.ratio() > ratio_ext_desc:
							return 1
						if ext_desc == extDesc:
							return 1
				return None
		elif int(config.misc.timer_show_movie_available.value) == 1:
			pos = bisect_left(self.titlelist_list, mytitle)
			try:
				return pos if self.titlelist_list[pos] == mytitle else None
			except IndexError:
				return None
		else:
			return None

	def removeFromTitleList(self, mytitle, shortDesc='', extDesc=''):
		if int(config.misc.timer_show_movie_available.value) > 1:
			is_in_short_desc_list = False
			is_in_ext_desc_list = False
			if mytitle in self.titlelist:
				x = self.titlelist[mytitle][0]
				if len(x):
					for short_desc in x:
						if short_desc == shortDesc:
							is_in_short_desc_list = True
							break
					if is_in_short_desc_list:
						x.remove(short_desc)
				y = self.titlelist[mytitle][1]
				if len(y):
					for ext_desc in y:
						if ext_desc == extDesc:
							is_in_ext_desc_list = True
							break
					if is_in_ext_desc_list:
						y.remove(ext_desc)
				if len(x):
					self.titlelist[mytitle][0] = x
				if len(y):
					self.titlelist[mytitle][1] = y
				if not len(x) and not len(y):
					del self.titlelist[mytitle]
		elif int(config.misc.timer_show_movie_available.value) == 1:
			idx = self.inTitleList(mytitle)
			if idx is not None:
				try:
					self.titlelist_list.pop(idx)
				except Exception:
					pass

	def addToTitleList(self, mytitle, shortDesc='', extDesc=''):
		if int(config.misc.timer_show_movie_available.value) > 1:
			if mytitle in self.titlelist:
				if isinstance(self.titlelist[mytitle][0], list) and shortDesc not in self.titlelist[mytitle][0]:
					x = self.titlelist[mytitle][0]
					x.append(shortDesc)
					self.titlelist[mytitle][0] = x
				else:
					self.titlelist[mytitle][0] = [shortDesc]
				if isinstance(self.titlelist[mytitle][1], list) and extDesc not in self.titlelist[mytitle][1]:
					x = self.titlelist[mytitle][1]
					x.append(extDesc)
					self.titlelist[mytitle][1] = x
				else:
					self.titlelist[mytitle][1] = [extDesc]
			else:
				self.titlelist[mytitle] = [[shortDesc], [extDesc]]
		elif int(config.misc.timer_show_movie_available.value) == 1:
			insort(self.titlelist_list, mytitle)

	def BackgroundTitleListUpdate(self):
		if int(config.misc.timer_show_movie_available.value) > 0:
			t = Thread(target=self.getTitleList, args=[])
			t.start()
			globalthreads.registerThread(t)

	def getTitleList(self):
		sqlcmd = 'SELECT ref,title,shortDesc, extDesc FROM  ' + self.table + ' WHERE IsTrash != 1'
		sqlret = self.executeSQL(sqlcmd, args=[], readonly=True)
		if sqlret and sqlret[0]:
			content = []
			rows = sqlret[1]
			self.disconnectDataBase(True)
			for row in rows:
				tmp_row = []
				for field in row:
					tmp_field = field
					if field and isinstance(str(field).encode('utf-8'), str):
						tmp_field = str(field).encode('utf-8')
					tmp_row.append(tmp_field)
				content.append(tmp_row)
			for x in content:
				if x[0]:
					orig_path = eServiceReference(x[0]).getPath()
					real_path = realpath(orig_path)
					if real_path[-3:] not in ('mp3', 'ogg', 'wav'):
						self.addToTitleList(x[1], x[2], x[3])

	def searchContent(self, data, fields="*", query_type="AND", exactmatch=False, compareoperator='', skipCheckExists=False):
		s_fields = [self.box_path, 'path', 'fname', 'ref']
		if (isinstance(fields, tuple) or isinstance(fields, list)) and len(fields):
			for field in fields:
				s_fields.append(field)
		elif isinstance(fields, str) and fields == "*":
			for key in self.fields:
				s_fields.append(key)
		elif isinstance(fields, str):
			s_fields.append(fields)
		s_fields.append(self.box_path)
		searchstr = None
		if 'title' in data:
			searchstr = data['title']
		elif 'shortDesc' in data:
			searchstr = data['shortDesc']
		elif 'extDesc' in data:
			searchstr = data['extDesc']
		if searchstr is not None:
			data[self.box_path] = searchstr
		res = self.searchDBContent(data, fields=s_fields, query_type=query_type, exactmatch=exactmatch, compareoperator=compareoperator)
		checked_res = []
		fields_count = len(s_fields)
		ref_idx = False
		video_dirs = self.getVideoDirs()
		for x in range(4, fields_count):
			if s_fields[x] == 'ref':
				ref_idx = x
				break
		if len(res):
			for movie in res:
				ret = []
				if skipCheckExists and movie[0] is not None:
					for x in range(4, fields_count):
						if ref_idx and ref_idx == x:
							if movie[3]:
								ret.append(movie[3] + movie[0])
						else:
							ret.append(movie[x])
					if ret not in checked_res:
						checked_res.append(ret)
				elif movie[0] is not None and exists(movie[0]):
					for x in range(4, fields_count):
						if ref_idx and ref_idx == x:
							if movie[3]:
								ret.append(movie[3] + movie[0])
							elif isdir(movie[0]):
								m = eServiceReference(eServiceReference.idFile, eServiceReference.flagDirectory, '')
								p = movie[0]
								if not p.endswith('/'):
									p += '/'
								m.setPath(p)
								ret.append(m.toString())
						else:
							ret.append(movie[x])
					if ret not in checked_res:
						checked_res.append(ret)
				else:
					do_update = False
					for y in video_dirs:
						if not movie[2] or not movie[1]:
							break
						pp = y + movie[2]
						p = y + movie[1]
						if not p.endswith('/'):
							p += '/'
						p += movie[2]
						p = str(p.encode('utf-8'))
						pp = str(pp.encode('utf-8'))
						if exists(p):
							do_update = True
						elif exists(pp):
							do_update = True
							p = pp
						if do_update:
							self.updateSingleEntry(movie[3] + p)
							for x in range(4, fields_count):
								if ref_idx and ref_idx == x:
									ret.append(movie[3] + p)
								else:
									ret.append(movie[x])
							if ret not in checked_res:
								checked_res.append(ret)
							break
		return checked_res

	def getTrashEntries(self, as_ref=False):
		fields = ['ref', 'fsize'] if as_ref else [self.box_path, 'fsize']
		entries = self.searchContent({'IsTrash': '1'}, fields=fields)
		ret = []
		fsize = 0.0
		for entry in entries:
			if entry[1]:
				fsize += float(entry[1])
			if as_ref:
				ret.append(eServiceReference(entry[0]))
			else:
				ret.append(entry[0])
		return (ret, fsize)

	def getDeprecatedTrashEntries(self, as_ref=False):
		now = time()
		diff_rec = config.usage.movielist_use_autodel_trash.value * 60.0 * 60.0 * 24.0
		diff_trash = config.usage.movielist_use_autodel_in_trash.value * 60.0 * 60.0 * 24.0
		fields = ['ref', 'begin', 'TrashTime'] if as_ref else [self.box_path, 'begin', 'TrashTime']
		entries = self.searchContent({'IsTrash': '1'}, fields=fields)
		ret = []
		rec_t = 0.0
		trash_t = 0.0
		link = config.usage.movielist_link_autodel_config.value == 'and' and True or False
		for entry in entries:
			rec_t = entry[1]
			trash_t = entry[2]
			if trash_t is None:
				trash_t = 0.0
			trash_t = float(trash_t)
			if rec_t is None:
				rec_t = 0.0
			rec_t = float(rec_t)
			append = False
			if link and diff_rec > 0 and diff_trash > 0 and rec_t > 0 and trash_t > 0:
				if now - rec_t >= diff_rec and now - trash_t >= diff_trash:
					append = True
			else:
				if now - rec_t >= diff_rec and diff_rec > 0 and rec_t > 0:
					append = True
				elif now - trash_t >= diff_trash and diff_trash > 0 and trash_t > 0:
					append = True
			if append:
				if as_ref:
					ret.append(eServiceReference(entry[0]))
				else:
					ret.append(entry[0])
		return ret

	def updateMovieDB(self):
		global hase_e2
		if not has_e2:
			return
		self.dbthread_id = current_thread().ident
		pathes = []
		is_killed = False
		this_job = None
		joblist = job_manager.getPendingJobs()
		for job in joblist:
			if job.name == self.dbthread_name and hasattr(job, 'database_job'):
				this_job = job
				break
		for folder in config.movielist.videodirs.value:
			if self.dbthread_kill:
				is_killed = True
				break
			for root, subFolders, files in walk(folder):
				if self.dbthread_kill:
					is_killed = True
					break
				pathes.append(root)
		if not is_killed:
			count = len(pathes)
			i = 0
			for folder in pathes:
				if self.dbthread_kill:
					break
				i += 1
				if count and this_job:
					progress = int(float(i) / float(count) * 100.0)
					this_job.database_job.setProgress(progress)
				path = folder
				if not folder.endswith('/'):
					path += '/'
				debugPrint(f"Add items of folder : {path}", LOGLEVEL.ALL)
				self.updateMovieDBPath(path, is_thread=True)
		self.stopBackgroundAction()

	def updateMovieDBSinglePath(self, path, is_thread=False):
		global hase_e2
		if not has_e2:
			return
		self.updateMovieDBPath(path, is_thread)
		self.stopBackgroundAction()

	def updateMovieDBPath(self, path, is_thread=False):
		global hase_e2
		if not has_e2:
			return
		m_list = []
		root = eServiceReference(eServiceReference.idFile, eServiceReference.flagDirectory, path + '/')
		serviceHandler = eServiceCenter.getInstance()
		hidden_items = []

		m_list = serviceHandler.list(root)
		hidden_entries_file = realpath(root.getPath()) + "/.hidden_movielist_entries"
		if exists(hidden_entries_file):
			with open(hidden_entries_file, "r") as f:
				for line in f:
					entry = line.strip()
					hidden_items.append(entry)
		if m_list is None:
			debugPrint("updating of movie database failed", LOGLEVEL.ERROR)
			return
		video_dirs = self.getVideoDirs()
		while 1:
			if self.dbthread_kill:
				break
			serviceref = m_list.getNext()
			if not serviceref.valid():
				break
			filepath = realpath(serviceref.getPath())
			if hidden_items and filepath in hidden_items:
				continue
			self.updateSingleEntry(serviceref, is_thread, video_dirs)

	def updateSingleEntry(self, serviceref, is_thread=False, video_dirs=[], with_box_path=False, isTrash=(False, 0)):
		if not video_dirs:
			video_dirs = self.getVideoDirs()
		if isinstance(serviceref, str):
			if not exists(serviceref):
				return
			filepath = realpath(serviceref)
			serviceref = eServiceReference(1, 0, filepath) if filepath.endswith('.ts') else eServiceReference(4097, 0, filepath)
		serviceHandler = eServiceCenter.getInstance()
		filepath = realpath(serviceref.getPath())
		trashfile = filepath + '.del'
		if filepath.endswith('_pvrdesc.ts'):
			return
		if isTrash[0]:
			if isTrash[1] == 1 and not exists(trashfile):
				try:
					mknod(trashfile)
				except OSError:
					pass
			else:
				if exists(trashfile):
					try:
						remove(trashfile)
					except OSError:
						pass
		is_dvd = None
		if serviceref.flags & eServiceReference.mustDescent:
			possible_path = ("VIDEO_TS", "video_ts", "VIDEO_TS.IFO", "video_ts.ifo")
			for mypath in possible_path:
				if exists(join(filepath, mypath)):
					is_dvd = True
					serviceref = eServiceReference(4097, 0, filepath)
					break
		if is_dvd is None and serviceref.flags & eServiceReference.mustDescent:
			fields = {self.box_path: filepath, 'IsDir': '1', 'fname': filepath, 'fsize': '0', 'ref': '2:47:1:0:0:0:0:0:0:0:', }
			if isTrash[0]:
				fields['IsTrash'] = str(isTrash[1])
				fields['TrashTime'] = str(0) if isTrash[1] == 0 else str(time())
			else:
				if exists(trashfile):
					fields['IsTrash'] = str(1)
					try:
						fields['TrashTime'] = str(stat(trashfile).st_mtime)
					except OSError:
						fields['TrashTime'] = str(time())
				else:
					return
			if with_box_path:
				self.updateUniqueData(fields, (self.box_path,))
			else:
				self.updateUniqueData(fields, ('fname', 'fsize'))
			if not is_thread:
				self.disconnectDataBase()
			return
		file_path = serviceref.getPath()
		file_extension = file_path.split(".")[-1].lower()
		if file_extension == "iso":
			serviceref = eServiceReference(4097, 0, file_path)
		if file_extension in ("dat",):
			return
		is_rec = 0
		if exists(file_path + '.rec'):
			is_rec = 1
		cur_item = basename(filepath)
		if cur_item.lower().startswith("timeshift_"):
			return
		info = serviceHandler.info(serviceref)
		if info is None:
			return
		m_db_begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
		m_db_tags = info.getInfoString(serviceref, iServiceInformation.sTags)
		m_db_fullpath = filepath
		m_db_path, m_db_fname = split(filepath)
		m_db_title = info.getName(serviceref)
		m_db_evt = info.getEvent(serviceref)
		m_db_shortDesc = ''
		if m_db_evt is not None:
			m_db_shortDesc = m_db_evt.getShortDescription()
			m_db_extDesc = m_db_evt.getExtendedDescription()
		else:
			m_db_title, m_db_extDesc = getExtendedMovieDescription(serviceref)
		m_db_ref = serviceref.toString().replace(serviceref.getPath(), '')
		m_db_begin = info.getInfo(serviceref, iServiceInformation.sTimeCreate)
		if is_rec:
			rec_file_c = []
			with open(file_path + '.rec') as f:
				rec_file_c = f.readlines()
			ret = str(rec_file_c[0]) if len(rec_file_c) >= 1 else ""
			ret = ret.strip()
			m_db_f_size = int(ret)
		else:
			m_db_f_size = self.getFileSize(m_db_fullpath)
		m_db_lastpos = -1
		m_db_progress = -1
		m_db_duration = info.getLength(serviceref)
		if video_dirs:
			for x in video_dirs:
				if m_db_path.startswith(x) or m_db_path == x[:-1]:
					m_db_path = m_db_path.lstrip(x)
					break
		m_db_autotags = ''
		autotags = config.movielist.autotags.value.split(';')
		desc = m_db_shortDesc.lower() + m_db_extDesc.lower()
		for tag in autotags:
			if desc[:80].find(tag.lower()) != -1 or desc[80:].find(tag.lower()) != -1:
				m_db_autotags += tag + ';'
		if m_db_duration < 0:
			m_db_duration = self.calcMovieLen(m_db_fullpath + '.cuts')
		if m_db_duration >= 0:
			m_db_lastpos, m_db_progress = self.getPlayProgress(m_db_fullpath + '.cuts', m_db_duration)
		fields = {'path': m_db_path,
				self.box_path: m_db_fullpath,
				'fname': m_db_fname,
				'title': m_db_title,
				'extDesc': m_db_extDesc,
				'shortDesc': m_db_shortDesc,
				'tags': m_db_tags,
				'ref': m_db_ref,
				'duration': str(m_db_duration),
				'lastpos': str(m_db_lastpos),
				self.box_lpos: str(m_db_lastpos),
				'progress': str(m_db_progress),
				'fsize': str(m_db_f_size),
				'begin': str(m_db_begin),
				'autotags': str(m_db_autotags),
				'IsRecording': str(is_rec),
			}

		search_fields = {self.box_path: m_db_fullpath, 'fname': m_db_fname, 'title': m_db_title, }
		is_in_db = self.searchContent(search_fields, fields=("fname",), query_type="AND", exactmatch=False, skipCheckExists=True)
		if isTrash[0]:
			fields['IsTrash'] = str(isTrash[1])
			if isTrash[1] == 0:
				fields['TrashTime'] = str(0)
				self.addToTitleList(m_db_title, m_db_shortDesc, m_db_extDesc)
			else:
				fields['TrashTime'] = str(time())
				if len(is_in_db):
					self.removeFromTitleList(m_db_title, m_db_shortDesc, m_db_extDesc)
		else:
			if exists(trashfile):
				fields['IsTrash'] = str(1)
				if len(is_in_db):
					self.removeFromTitleList(m_db_title, m_db_shortDesc, m_db_extDesc)
				try:
					fields['TrashTime'] = str(stat(trashfile).st_mtime)
				except OSError:
					fields['TrashTime'] = str(time())
			else:
				self.addToTitleList(m_db_title, m_db_shortDesc, m_db_extDesc)
		if with_box_path:
			self.updateUniqueData(fields, (self.box_path,))
		else:
			self.updateUniqueData(fields, ('fname', 'fsize'))
		if not is_thread:
			self.disconnectDataBase()

	def calcMovieLen(self, fname):
		if exists(fname):
			try:
				with open(fname, "rb") as f:
					packed = f.read()
				while len(packed) > 0:
					packedCue = packed[:12]
					packed = packed[12:]
					cue = unpack('>QI', packedCue)
					if cue[1] == 5:
						movie_len = cue[0] / 90000
						return movie_len
			except Exception as ex:
				debugPrint("failure at getting movie length from cut list", LOGLEVEL.ERROR)
		return -1

	def getPlayProgress(self, moviename, movie_len):
		cut_list = []
		if exists(moviename):
			try:
				f = open(moviename, "rb")
				packed = f.read()
				f.close()

				while len(packed) > 0:
					packedCue = packed[:12]
					packed = packed[12:]
					cue = unpack('>QI', packedCue)
					cut_list.append(cue)
			except Exception as ex:
				debugPrint("failure at downloading cut list", LOGLEVEL.ERROR)
		last_end_point = None
		if len(cut_list):
			for (pts, what) in cut_list:
				if what == 3:
					last_end_point = pts / 90000
		try:
			movie_len = int(movie_len)
		except ValueError:
			play_progress = 0
			movie_len = -1
		if movie_len > 0 and last_end_point is not None:
			play_progress = (last_end_point * 100) / movie_len
		else:
			play_progress = 0
			last_end_point = 0
		if play_progress > 100:
			play_progress = 100
		return (last_end_point, play_progress)


moviedb = MovieDataBase()
moviedb.BackgroundTitleListUpdate()


def isMovieinDatabase(title_name, shortdesc, extdesc, short_ratio=0.95, ext_ratio=0.85):
	movie = None
	movie_found = False
	s = {'title': str(title_name)}
	trash_movies = []
	if config.usage.movielist_use_moviedb_trash.value:
		trash_movies = moviedb.getTrashEntries()[0]
	print("[MovieDB] search for existing media file with title: ", str(title_name))
	for x in moviedb.searchContent(s, ('title', 'shortDesc', 'extDesc'), query_type="OR", exactmatch=False):
		movie_found = False
		if shortdesc and shortdesc != '' and x[1]:
			sequenceMatcher = SequenceMatcher(" ".__eq__, shortdesc, str(x[1]))
			ratio = sequenceMatcher.ratio()
			print(f"[MovieDB] shortdesc movie ratio {ratio:f} - {len(shortdesc)} - {len(x[1])}")
			if shortdesc in x[1] or (short_ratio < ratio):
				movie = x
				movie_found = True
				print("[MovieDB] found movie with similiar short description -> skip this event")
		if movie_found:
			if extdesc and x[2]:
				sequenceMatcher = SequenceMatcher(" ".__eq__, extdesc, str(x[2]))
				ratio = sequenceMatcher.ratio()
				print(f"[MovieDB] extdesc movie ratio {ratio:f} - {len(extdesc)} - {len(x[1])}")
				if ratio < ext_ratio:
					movie = None
					movie_found = False
				else:
					movie_found = True
					movie = x
					print("[MovieDB] found movie with similiar short and extended description -> skip this event")
					break
			else:
				print("[MovieDB] found movie with similiar short description -> skip this event")
				movie_found = True
				movie = x
				break
		if extdesc and x[2] and not movie_found:
			sequenceMatcher = SequenceMatcher(" ".__eq__, extdesc, str(x[2]))
			ratio = sequenceMatcher.ratio()
			print(f"[MovieDB] extdesc movie ratio {ratio:f} - {len(extdesc)} - {len(x[1])}")
			if extdesc in x[2] or (ext_ratio < ratio):
				movie = x
				movie_found = True
				print("[MovieDB] found movie with similiar extended description -> skip this event")
				break
	if movie_found:
		real_path = realpath(eServiceReference(movie[0]).getPath()) if movie else ""
		movie_found = True if real_path not in trash_movies or exists(real_path + '.del') else False
	return movie_found


class MovieDBUpdateBase:
	def __init__(self):
		self.navigation = None

	def getNavigation(self):
		if not self.navigation:
			import NavigationInstance
			if NavigationInstance:
				self.navigation = NavigationInstance.instance
		return self.navigation

	def getRecordings(self):
		recordings = []
		nav = self.getNavigation()
		if nav:
			recordings = nav.getRecordings()
		return recordings

	def getInstandby(self):
		from Screens.Standby import inStandby
		return inStandby


class MovieDBUpdate(MovieDBUpdateBase):

	def __init__(self):
		MovieDBUpdateBase.__init__(self)
		self.updateTimer = eTimer()
		self.updateTimer.callback.append(self.startUpdate)
		self.timerintervall = 30
		self.longtimerintervall = 180

	def updateMovieDBAuto(self, configElement):
		if config.usage.movielist_use_moviedb_autoupdate.value:
			self.updateTimer.startLongTimer(self.timerintervall)

	def startUpdate(self):
		self.updateTimer.stop()
		if self.getRecordings():
			debugPrint("update cancelled - there are running records", LOGLEVEL.INFO)
			self.updateTimer.startLongTimer(self.longtimerintervall)
			return
		jobs = (job_manager.getPendingJobs())
		if jobs:
			for job in jobs:
				if job.name.lower().find('database') != -1:
					debugPrint("update cancelled - there is still a running  database job", LOGLEVEL.INFO)
					return
		if self.getInstandby():
			debugPrint("start auto update of moviedb", LOGLEVEL.INFO)
			moviedb.BackgroundDBUpdate(moviedb.updateMovieDB)
		else:
			debugPrint("update cancelled - not in Standby", LOGLEVEL.INFO)


moviedbupdate = MovieDBUpdate()


def backgroundDBUpdate():
	moviedb.BackgroundDBUpdate(moviedb.updateMovieDB)


functionTimer.add(("moviedbupdate", {"name": _("update movie database (full)"), "fnc": "backgroundDBUpdate"}))

# TODO
#functionTimer.add(("movietrashclean", {"name": _("clear movie trash"), "imports": "Components.MovieTrash", "fnc": "movietrash.cleanAll"}))
