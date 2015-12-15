"""
   Server side components for your app
   Srivatsan Ramanujam <vatsan.cs@utexas.edu>, 28-May-2015
"""

import os
import json
from flask import Flask, render_template, jsonify, request, send_file, make_response
from flask.ext.assets import Bundle, Environment
import logging
from dbconnector import DBConnect, DEFAULT_PORT
from sql.queries import *
import urllib2
import numpy as np
import StringIO
from array import array
import ast

#init app
app = Flask(__name__)

#init logger
logging.basicConfig(level= logging.DEBUG if not os.getenv('PORT') \
        else logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

#init flask assets
bundles = {
    'user_js': Bundle(
            #all your javascript files in static folder, go here
            'js/heatmap.js',
            filters='jsmin' if os.getenv('PORT') else None, #minify if deploying on CF
            output='gen/user.js',
        ),
    'user_css': Bundle(
            #all your css files in the static folder, go here
           'css/custom.css',
            filters='jsmin' if os.getenv('PORT') else None, #minify if deploying on CF
            output='gen/user.css'
        )   
}
assets = Environment(app)
assets.register(bundles)

#Initialize database connection objects
conn = DBConnect(logger)

def index():
    """
       Render homepage
    """
    return render_template('index.html', title='dspcfboilerplate')

@app.route('/')
@app.route('/home')
def home():
    """
       Homepage
    """
    logger.debug('In home()')
    return render_template('cbirapp_home.html')

@app.route('/about')
def about():
    """
       About page, listing background information about the app
    """
    logger.debug('In about()')
    return render_template('about.html')

@app.route('/contact')
def contact():
    """
       Contact page
    """
    logger.debug('In contact()')
    return render_template('contact.html')
    
@app.route('/settings')
def settings():
    """
       Settings page (for model building)
    """
    logger.debug('In settings()')
    return render_template('settings.html')    

@app.route('/<path:path>')
def static_proxy(path):
    """
       Serving static files
    """
    logger.debug('In static_proxy()')
    return app.send_static_file(path)

@app.route('/_hmap')    
def sample_heatmap():
    """
        Populate a sample heatmap
    """
    global conn
    INPUT_SCHEMA = 'public'
    INPUT_TABLE = 'sample_heatmap'
    sql = fetch_sample_data_for_heatmap(INPUT_SCHEMA, INPUT_TABLE)
    logger.info(sql)
    df = conn.fetchDataFrame(sql)
    logger.info('sample_heatmap: {0} rows'.format(len(df)))
    return jsonify(hmap=[{'machine_id':r['id'], 'hour':r['hour'], 'prob':r['prob']} for indx, r in df.iterrows()])    

@app.route('/_search',methods=['GET', 'POST'])
def search():
    from PIL import Image
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    import StringIO
    if request.method == "POST":
        global conn
        logger.info(request.form['search'])
        img_req = urllib2.urlopen(request.form['search']) 
        logger.info('query image opened')
        img_arr = np.asarray(bytearray(img_req.read()), dtype=np.int8)
        logger.info('query image read')
        buf = img_arr.tostring()
        buff = StringIO.StringIO() 
        buff.write(buf)
        buff.seek(0)
        im = Image.open(buff)
        f, axarr = plt.subplots(4,3)
        f.patch.set_facecolor('white')
        f.set_size_inches(18, 12)
        axarr[0, 1].imshow(im)
        axarr[0, 1].axis('off')
        axarr[0, 1].set_title('Query Image', {'fontsize':18, 'fontweight' : 'bold'})
        axarr[0, 0].axis('off')
        axarr[0, 2].axis('off')
        img_arr_str = str(img_arr.tolist()).replace('[','').replace(']','')
        sql = '''select cbirapp.retrieve_images('{d_arr}');'''.format(d_arr=img_arr_str)
        images = conn.executeQuery(sql)
        logger.info('Backend UDF called')        
        for i in range(0, 9):
            I = images[i]
            image = ast.literal_eval(I[0])['img']
            buf = image.split(',')
            buf = map(int, buf)
            buf = array('b',buf)
            buf = buf.tostring()
            buff = StringIO.StringIO() 
            buff.write(buf)
            buff.seek(0)
            im = Image.open(buff)
            if (i % 3 == 0):
                j = 0
            if (i < 3):
                axarr[1, j].imshow(im)
                axarr[1, j].axis('off')
                if (j == 1):
                    axarr[1, j].set_title('Retrieved Images', {'fontsize':18, 'fontweight' : 'bold'})
                j = j + 1
            elif (i >=3 and i < 6):
                axarr[2, j].imshow(im)
                axarr[2, j].axis('off')
                j = j + 1
            elif (i >= 6 and i < 9):
                axarr[3, j].imshow(im)
                axarr[3, j].axis('off')
                j = j + 1
        canvas=FigureCanvas(f)
        png_output = StringIO.StringIO()
        canvas.print_png(png_output)
        response=make_response(png_output.getvalue())
        response.headers['Content-Type'] = 'image/png'
        return response
    return render_template('cbirapp_home.html')

def main():
    """
       Start the application
    """
    app_port = int(os.getenv('PORT')) if os.getenv('PORT') else DEFAULT_PORT
    app.run(host='0.0.0.0', debug= True if not os.getenv('PORT') else False, port = app_port)
