import gradio as gr
import zipfile
import json
import pandas as pd
from tensorflow.keras.models import model_from_json
from collections import Counter

def extract_tm_info(tm_path):
    with zipfile.ZipFile(tm_path, 'r') as zip_ref:
        with zip_ref.open('manifest.json') as f:
            manifest = json.load(f)
        return {
            'type': manifest.get('type', 'N/A'),
            'version': manifest.get('version', 'N/A'),
            'epochs': manifest.get('appdata', {}).get('trainEpochs', 'N/A'),
            'batch_size': manifest.get('appdata', {}).get('trainBatchSize', 'N/A'),
            'learning_rate': manifest.get('appdata', {}).get('trainLearningRate', 'N/A')
        }

def extract_zip_info(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        metadata = model_json = None
        weights_file = None

        for file in file_list:
            if 'metadata.json' in file:
                with zip_ref.open(file) as f:
                    metadata = json.load(f)
            elif 'model.json' in file:
                with zip_ref.open(file) as f:
                    model_json = json.load(f)
            elif 'model.weights.bin' in file:
                weights_file = file

        if model_json:
            model_topology_json = model_json['modelTopology']
            model_json_string = json.dumps(model_topology_json)
            model = model_from_json(model_json_string)
            summary = {'layer_counts': Counter()}
            extract_layer_info(model_topology_json['config']['layers'], summary)
            layer_counts_text = ', '.join([f'{k}: {v}' for k, v in summary['layer_counts'].items()])
        else:
            layer_counts_text = "Modelo não encontrado"

        weights_info = {'size_bytes': zip_ref.getinfo(weights_file).file_size} if weights_file else {'size_bytes': 'Não encontrado'}

        return {
            'metadata': metadata if metadata else 'Metadados não encontrados',
            'model_summary': layer_counts_text,
            'weights_info': weights_info
        }

#####
def extract_layer_info(layers, summary):
    for layer in layers:
        class_name = layer['class_name']
        summary['layer_counts'][class_name] += 1
        if class_name in ['Sequential', 'Model']:
            sub_layers = layer['config']['layers']
            extract_layer_info(sub_layers, summary)

def analyze_files(tm_file, zip_file):
    results = {}
    if tm_file is not None:
        tm_info = extract_tm_info(tm_file.name)
        results['tm_info'] = tm_info
    if zip_file is not None:
        zip_info = extract_zip_info(zip_file.name)
        results['zip_info'] = zip_info
    return pd.DataFrame([results]).to_html(escape=False)

iface = gr.Interface(
    fn=analyze_files,
    inputs=[
        gr.File(label="Upload .tm File"),
        gr.File(label="Upload .zip File")
    ],
    outputs=gr.HTML(),
    title="GTM-Scope",
    description="Upload a .tm or .zip file to extract its information. A .tm or .zip (with json) file is generated by Google Teachable Machine. The .tm file provides basic model information such as type, version, training parameters, while the .zip file (with json), obtained after training and exporting the model in Tensorflow.js format, offers detailed insights including model structure, weight sizes, and other metadata."
)
#...
iface.launch(debug=True)
