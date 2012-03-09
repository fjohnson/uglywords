import webapp2
import uc
import codecs

class MainPage(webapp2.RequestHandler):
  def get(self):
      self.response.out.write(open('input.html').read())

class textProcessor(webapp2.RequestHandler):
  def post(self):
      input_text = self.request.get('text')
      self.response.out.write(uc.html_output(input_text))

class dictdisplay(webapp2.RequestHandler):
  def get(self):
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.headers['charset']='iso8859'
      self.response.out.write(codecs.open('dict/words',encoding="iso8859").read())

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/checktext',textProcessor),
                               ('/dict/words',dictdisplay)],
                              debug=True)
