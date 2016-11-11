 # -*- coding:utf-8 -*-

import requests,urlparse,time,re,json,threading,hashlib;
from bs4 import BeautifulSoup;

session = None
info = {
  'current': {}
}
userAgnet = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36';
headers = {
  'User-Agent': userAgnet
};

def init():
  global session;
  session = requests.Session();
  initResp = session.get('http://passport2.chaoxing.com/login?fid=1226&refer=http://i.mooc.chaoxing.com/space/index.shtml');

def login(user, password):
  global session, info;
  varImgResp = session.get('http://passport2.chaoxing.com/num/code?' + str(int(time.time())));

  file = open('varImg.png', 'wb+');
  file.write(varImgResp.content);
  file.close();
  print 'please input varImg:'
  varNum = raw_input();

  data = {
    'refer_0x001': 'http%3A%2F%2Fi.mooc.chaoxing.com%2Fspace%2Findex.shtml',
    'pid': '-1',
    'pidName': '',
    'fid': '1226',
    'fidName': '长春师范大学',
    'allowJoin': 0,
    'isCheckNumCode': 1,
    'f': 0,
    'productid': '',
    'uname': user,
    'password': password,
    'numcode': varNum
  }

  loginResp = session.post('http://passport2.chaoxing.com/login?refer=http%3A%2F%2Fi.mooc.chaoxing.com%2Fspace%2Findex.shtml', data=data, allow_redirects=False);
  info['current']['uid'] = loginResp.cookies['UID'];

  soup = BeautifulSoup(loginResp.content);
  has_error = soup.select_one('#show_error');

  return has_error is None;

def readCourse(course):
  global session, headers;
  courseResp = session.get(course['url'], headers=headers);

  soup = BeautifulSoup(courseResp.content)
  return map(lambda course: {'title': course['title'], 'url': 'http://mooc1-1.chaoxing.com' + course['href']}, soup.select('.clearfix > .articlename > a[href]'));

def readInfo():
  global session, headers, info;
  coursesResp = session.get('http://mooc1-1.chaoxing.com/visit/courses', headers=headers);

  soup = BeautifulSoup(coursesResp.content);
  items = soup.select('.ulDiv > ul > li > .Mconright > h3 > a');
  courses = map(lambda course: {'title': course['title'], 'url': 'http://mooc1-1.chaoxing.com' + course['href']}, items);

  info['courses'] = map(readCourse, courses);

def selectClass():
  global session, headers, info;

  courseId = '';
  knowledgeId = '';
  clazzId = '';

  courses = info['courses'];

  for course in courses:
    for item in course:
      isPassed = False;
      parseResult = urlparse.urlparse(item['url']);
      queryResult = urlparse.parse_qs(parseResult.query)

      print queryResult

      courseId = queryResult[u'courseId'][0];
      knowledgeId = queryResult[u'chapterId'][0];
      clazzId = queryResult[u'clazzid'][0];

      print courseId, knowledgeId, clazzId

      cardRequest = session.get('https://mooc1-1.chaoxing.com/knowledge/cards?clazzid=' + clazzId + '&courseid=' + courseId + '&knowledgeid=' + knowledgeId + '&num=0&v=20160407-1', headers=headers);
      matchObj = re.findall(r'try{\n\s+mArg\s=\s(.*)\n}catch\(e\){\n}' ,cardRequest.content)[0][0: -1];
      
      jsonObj = json.loads(matchObj);

      defaults = jsonObj['defaults'];

      print defaults;

      info['current']['reportTimeInterval'] = defaults['reportTimeInterval'];

      attachments = jsonObj['attachments'][0];
      if attachments.has_key('isPassed'):
        isPassed = attachments['isPassed']
      
      if isPassed is not True :
        info['currentSelectCourse'] = attachments;

        info['current']['courseId'] = courseId;
        info['current']['knowledgeId'] = knowledgeId;
        info['current']['clazzId'] = clazzId;

        print item['title'], 'is not Passed'
        return;
      else:
        print item['title'], 'is Passed'

def makeEnc(clazzId, userid, jobid, objectid, playtime, duration, cliptime):
  salt = 'd_yHJ!$pdA~5';
  src = '[{0}][{1}][{2}][{3}][{4}][{5}][{6}][{7}]'.format(clazzId, userid, jobid, objectid, str(playtime * 1000), salt, str(duration * 1000), cliptime);
  print src
  m2 = hashlib.md5();
  m2.update(src);
  return str(m2.hexdigest());

def sendHeartBeat():
  global session, info, headers;

  current = info['current'];

  dtoken = current['dtoken'];
  objectId = current['objectId'];
  duration = current['duration'];
  otherInfo = current['otherInfo'];
  clazzId = current['clazzId'];
  type = current['type'];
  jobid = current['jobid'];
  userid = current['uid'];
  clipTime = '0_{0}'.format(duration);
  headOffset = current['headOffset'];
  startTime = current['startTime'];
  nowTime = time.time();
  diff = headOffset + nowTime - startTime;
  playTime = int(diff) if diff < duration else duration;
  isdrag = '3' if diff < duration else '4';
  enc = makeEnc(clazzId, userid, jobid, objectId, playTime, duration, clipTime);

  params = {
    'objectId': objectId,
    'duration': duration,
    'otherInfo': otherInfo,
    'rt': '0.9',
    'clazzId': clazzId,
    'clipTime': clipTime,
    'jobid': jobid,
    'userid': userid,
    'view': 'pc',
    'playingTime': playTime,
    'isdrag': isdrag,
    'enc': enc,
    'dtype': type
  }

  logResp = session.get('https://mooc1-1.chaoxing.com/multimedia/log/' + dtoken, params=params, headers=headers);

  print logResp.content

  return diff < duration

def processCourse():
  if sendHeartBeat() is True:
    info['current']['timer'] = threading.Timer(info['current']['reportTimeInterval'], processCourse);
    info['current']['timer'].start();
  else:
    selectClass()

def classBegin():
  global info, headers, session;
  headOffset = 0;
  jobid='';
  objectId='';
  mid='';
  playTime='';
  otherInfo='';
  type='';

  attachments = info['currentSelectCourse'];

  if attachments.has_key('headOffset'):
    headOffset = attachments['headOffset'];
  if attachments.has_key('jobid'):
    jobid = attachments['jobid'];
  if attachments.has_key('objectId'):
    objectId = attachments['objectId'];
  if attachments.has_key('mid'):
    mid = attachments['mid'];
  if attachments.has_key('playTime'):
    playTime = attachments['playTime'];
  if attachments.has_key('otherInfo'):
    otherInfo = attachments['otherInfo'];
  if attachments.has_key('type'):
    type = attachments['type'];

  info['current']['headOffset'] = headOffset;
  info['current']['jobid'] = jobid;
  info['current']['objectId'] = objectId;
  info['current']['playTime'] = playTime;
  info['current']['otherInfo'] = otherInfo;
  info['current']['type'] = type;

  queryResp = session.get('https://mooc1-1.chaoxing.com/ananas/status/{0}?k=1226&_dc={1}'.format(objectId, str(int(time.time()))), headers=headers)

  jsonObj = json.loads(queryResp.content);

  info['current']['duration'] = jsonObj['duration'];
  info['current']['dtoken'] = jsonObj['dtoken'];

  info['current']['startTime'] = time.time();
  processCourse();

if __name__=='__main__':
  init();
  isLoginSuccess = login('1302340102', '951210');

  if isLoginSuccess:
    print 'login success'
    readInfo();
    selectClass();

    classBegin();
  else:
    print 'login failed'