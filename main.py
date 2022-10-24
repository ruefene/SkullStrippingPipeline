import os
import shutil
from datetime import datetime
from typing import Tuple
import threading

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session,
    make_response,
    jsonify)
from werkzeug.utils import secure_filename

from inference import Inferer
from frontend import get_sequence_infos, generate_modality_config

# Create the Flask app
app = Flask(__name__)
app.config.update(
    TESTING=True,
    SECRET_KEY='192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf')


def get_model_files(model_dir: str) -> Tuple[str, ...]:
    # Search for all model files
    model_files = []

    for root, _, files in os.walk(model_dir):
        for file in files:
            if file.endswith('.pth'):
                model_files.append(os.path.join(root, file))

    return tuple(model_files)


class BackgroundWorker(threading.Thread):

    def __init__(self,
                 input_path: str,
                 output_path: str,
                 model_path: str,
                 job_id: str,
                 sequences: dict
                 ):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.model_path = model_path
        self.job_id = job_id
        self.sequences = sequences

        self.daemon = True

    def run(self):
        _ = generate_modality_config(self.input_path, self.sequences)
        model_file_path = get_model_files(self.model_path)[0]

        inferer = Inferer(self.input_path, self.output_path, model_file_path, self.job_id)
        inferer.execute()


@app.before_first_request
def initialize():
    session['is_cancelable'] = True
    session['is_uploaded'] = False
    session['is_executable'] = False
    session['is_downloadable'] = False
    session['image_series'] = {}
    session['current_input_file'] = None
    session['current_job_id'] = None


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', **session)


@app.route('/cancel_process', methods=['POST'])
def cancel_process():
    if not session['is_cancelable']:
        return redirect('/')

    for entity in os.scandir(os.environ.get('INPUT_DATA_DIR')):
        if entity.is_dir():
            shutil.rmtree(entity.path)
        else:
            os.remove(entity.path)

    for entity in os.scandir(os.environ.get('OUTPUT_DATA_DIR')):
        if entity.is_dir():
            shutil.rmtree(entity.path)
        else:
            os.remove(entity.path)

    for entity in os.scandir(os.environ.get('SCRATCH_DATA_DIR')):
        if entity.is_dir():
            shutil.rmtree(entity.path)
        else:
            os.remove(entity.path)

    initialize()

    return make_response(render_template('index.html', **session), 200)


@app.route('/upload/', methods=['POST'])
def upload():
    try:
        # Get the uploaded file
        if request.method == 'POST':
            f = request.files['file']

            # check if the file extension matches
            if not f.filename.endswith('.zip'):
                return redirect('/')

            # save the current input file in the input directory
            session['current_input_file'] = secure_filename(f.filename)
            input_file_path = os.path.join(os.environ.get('INPUT_DATA_DIR'), secure_filename(f.filename))
            f.save(input_file_path)

            # create the job directories in the scratch directory
            session['current_job_id'] = str(hex(int(datetime.utcnow().strftime('%Y%m%d%H%M%S%f')))[2:])
            scratch_file_path = os.path.join(os.environ.get('SCRATCH_DATA_DIR'), session['current_job_id'])
            os.makedirs(scratch_file_path)

            # unpack the input data and copy to scratch directory
            shutil.unpack_archive(input_file_path, scratch_file_path)

            # get the sequences
            session['image_series'] = get_sequence_infos(scratch_file_path)

            # set the global variables
            session['is_uploaded'] = True

            return make_response(jsonify({'message': 'Upload successful', 'job_id': session['current_job_id']}), 200)

    except Exception as e:
        return make_response(jsonify({'message': 'Upload failed', 'error': str(e)}), 500)


@app.route('/assign/', methods=['POST'])
def assign_modality():
    if request.method == 'POST':

        t1_uid = eval(request.data).get('T1')
        t2_uid = eval(request.data).get('T2')

        try:
            cleaned_form_data = {t1_uid: 'T1', t2_uid: 'T2'}
            scratch_path = os.path.join(os.environ.get('SCRATCH_DATA_DIR'), session['current_job_id'])
            output_path = os.environ.get('OUTPUT_DATA_DIR')
            task = BackgroundWorker(input_path=scratch_path,
                                    output_path=output_path,
                                    model_path=os.environ.get('MODEL_DIR_PATH'),
                                    job_id=session['current_job_id'],
                                    sequences=cleaned_form_data)
            task.start()

            # set the session variables
            session['is_cancelable'] = True
            session['is_executable'] = False
            session['is_downloadable'] = False

        except Exception as e:
            print(e)
            response = make_response(jsonify({'message': 'Could not execute the process.', 'error': str(e)}), 500)
            return response

        response = make_response(jsonify({'message': 'Execution successful', 'job_id': session['current_job_id']}), 200)
        return response



@app.route('/fileexist/', methods=['GET'])
def file_exists():
    if request.method == 'GET':
        job_id = request.args.get('job_id')
        try:
            output_file_path = os.path.join(os.environ.get('OUTPUT_DATA_DIR'), job_id + '.zip')
            if os.path.exists(output_file_path):
                session['is_downloadable'] = True
                return make_response(jsonify({'message': 'File exists', 'result': 'true'}), 200)
            else:
                return make_response(jsonify({'message': 'File does not exist', 'result': 'false'}), 200)
        except Exception as e:
            return make_response(jsonify({'message': 'Could not check if file exists', 'error': str(e)}), 500)


@app.route('/download', methods=['POST', 'GET'])
def download():
    # get the paths
    if request.method == 'GET':
        job_id = request.args.get('job_id')
        output_path = os.environ.get('OUTPUT_DATA_DIR')
        output_file_path = os.path.join(output_path, job_id + '.zip')

        # set the session variables
        session['current_input_file'] = None
        session['current_job_id'] = None
        session['is_uploaded'] = False
        session['is_cancelable'] = True
        session['is_executable'] = False
        session['is_downloadable'] = False
        session['image_series'] = {}

        return make_response(send_file(output_file_path, as_attachment=True), 200)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
