import os
import shutil
from datetime import datetime
from typing import Tuple

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    session,
    url_for,
    jsonify)
from werkzeug.utils import secure_filename

from inference import Inferer
from frontend import get_sequence_infos, generate_modality_config

# Create the Flask app
app = Flask(__name__)
app.config.update(
    TESTING=True,
    SECRET_KEY='192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf',
)


def get_model_files(model_dir: str) -> Tuple[str, ...]:
    # Search for all model files
    model_files = []

    for root, _, files in os.walk(model_dir):
        for file in files:
            if file.endswith('.pth'):
                model_files.append(os.path.join(root, file))

    return tuple(model_files)


@app.before_first_request
def initialize():
    # session.setdefault('is_cancelable', False)
    # session.setdefault('is_uploaded', False)
    # session.setdefault('is_executable', False)
    # session.setdefault('is_downloadable', False)
    # session.setdefault('image_series', {})
    # session.setdefault('current_input_file', None)
    # session.setdefault('current_job_id', None)

    session['is_cancelable'] = True
    session['is_uploaded'] = False
    session['is_executable'] = False
    session['is_downloadable'] = False
    session['image_series'] = {}
    session['current_input_file'] = None
    session['current_job_id'] = None


@app.route('/')
def index():
    context = {'is_cancelable': session['is_cancelable'],
               'is_uploaded': session['is_uploaded'],
               'image_series': session['image_series'],
               'executable': session['is_executable'],
               'is_downloadable': session['is_downloadable']}
    return render_template('index.html', **context)


@app.route('/cancel_process', methods=['POST'])
def cancel_process():
    if not session['is_cancelable']:
        return redirect('/')

    if isinstance(session['current_input_file'], str):
        input_file_path = os.path.join(os.environ.get('INPUT_DATA_DIR'), session['current_input_file'])
        try:
            os.remove(input_file_path)
        except FileNotFoundError:
            pass

    if isinstance(session['current_job_id'], str):
        scratch_dir_path = os.path.join(os.environ.get('SCRATCH_DATA_DIR'), session['current_job_id'])
        try:
            shutil.rmtree(scratch_dir_path)
        except FileNotFoundError:
            shutil.rmtree(os.environ.get('SCRATCH_DATA_DIR'))

    initialize()

    return redirect('/')


@app.route('/upload/', methods=['POST'])
def upload():
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

    return redirect('/')


@app.route('/assign/', methods=['POST'])
def assign_modality():
    if request.method == 'POST':
        scratch_path = os.path.join(os.environ.get('SCRATCH_DATA_DIR'), session['current_job_id'])

        # validate the form data
        form_data = dict(request.form)
        cleaned_form_data = {}
        for i, (key, value) in enumerate(form_data.items()):
            if value in ('T1', 'T2'):
                cleaned_form_data.update({key: value})
            else:
                cleaned_form_data.update({key: str(i) + '_unknown'})

        result = generate_modality_config(scratch_path, cleaned_form_data)

        session['is_executable'] = result

        if not result:
            return redirect('/cancel_process')

    return redirect('/')


@app.route('/execute/', methods=['POST'])
def execute_process():
    if request.method == 'POST':
        # get the paths
        scratch_path = os.path.join(os.environ.get('SCRATCH_DATA_DIR'), session['current_job_id'])
        output_path = os.environ.get('OUTPUT_DATA_DIR')

        # get the model files
        model_file_path = get_model_files(os.environ.get('MODEL_DIR_PATH'))[0]

        # run the inference
        print('Executing inference...')
        # try:
        Inferer(scratch_path,
                output_path,
                model_file_path,
                session['current_job_id']).execute()
        # except Exception:
        #     print('Inference failed!')
        #     return redirect('/cancel_process')

        # set the session variables
        session['is_cancelable'] = False
        session['is_executable'] = False
        session['is_downloadable'] = True

        # remove the scratch file
        shutil.rmtree(scratch_path)

        # remove the input file
        input_file_path = os.path.join(os.environ.get('INPUT_DATA_DIR'), session['current_input_file'])
        os.remove(input_file_path)

        return redirect('/')


@app.route('/download/', methods=['POST', 'GET'])
def download():
    # if request.method == 'POST':

    # get the paths
    output_path = os.environ.get('OUTPUT_DATA_DIR')
    output_file_path = os.path.join(output_path, session['current_job_id'] + '.zip')

    # remove the output directory
    # os.remove(output_file_path)

    # set the session variables
    file_name = session['current_job_id'] + '.zip'
    session['current_input_file'] = None
    session['current_job_id'] = None
    session['is_uploaded'] = False
    session['is_cancelable'] = True
    session['is_executable'] = False
    session['is_downloadable'] = False
    session['image_series'] = {}

    return send_file(os.path.abspath(output_file_path),
                     mimetype='application/zip',
                     as_attachment=True,
                     download_name=file_name)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
