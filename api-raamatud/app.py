from flask import Flask, request, jsonify
from azure.storage.blob import BlobServiceClient
import os
import json
import requests
from flask_cors import CORS
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/raamatud/*": {"origins": "*"}, r"/raamatu_otsing/*": {"origins": "*"}})


blob_connection_string = os.getenv("APPSETTING_AzureWebJobsStorage")
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
blob_container_name = os.getenv("APPSETTING_blob_container_name")
if not blob_connection_string or not blob_container_name:
    raise RuntimeError("Keskkonnamuutujad AzureWebJobsStorage või blob_container_name puuduvad")

app.logger.info(f"Connection string: {blob_connection_string}")
app.logger.info(f"Container name: {blob_container_name}")

def blob_konteineri_loomine(nimi):
    container_client = blob_service_client.get_container_client(container=nimi)
    if not container_client.exists():
        blob_service_client.create_container(nimi)

def blob_raamatute_nimekiri():
    container_client = blob_service_client.get_container_client(container=blob_container_name)
    return [blob.name for blob in container_client.list_blobs()]

def blob_alla_laadimine(faili_nimi):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    return blob_client.download_blob().content_as_text()

def blob_ules_laadimine_sisu(faili_nimi, sisu):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    blob_client.upload_blob(sisu, overwrite=True)

def blob_kustutamine(faili_nimi):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    blob_client.delete_blob()

blob_konteineri_loomine(blob_container_name)

@app.route('/raamatud/', methods=['GET'])
def raamatu_nimekiri():
    raamatud = [blob.split('.')[0] for blob in blob_raamatute_nimekiri() if blob.endswith(".txt")]
    return jsonify({"raamatud": raamatud}), 200

@app.route('/raamatud/<book_id>', methods=['GET'])
def raamatu_allatombamine(book_id):
    if not book_id.isnumeric():
        return jsonify({"error": "Vigane raamatu ID"}), 400
    try:
        raamatu_sisu = blob_alla_laadimine(f"{book_id}.txt")
        return raamatu_sisu, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception:
        return {}, 404

@app.route('/raamatud/<book_id>', methods=['DELETE'])
def raamatu_kustutamine(book_id):
    if not book_id.isnumeric():
        return jsonify({"error": "Vigane raamatu ID"}), 400
    try:
        blob_kustutamine(f"{book_id}.txt")
        return jsonify({}), 204
    except Exception:
        return {}, 404

@app.route('/raamatud/', methods=['POST'])
def raamatu_lisamine():
    input_data = json.loads(request.data)
    book_id = input_data.get("raamatu_id")
    if not book_id or not book_id.isnumeric():
        return jsonify({"error": "Vigane sisend"}), 400

    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        try:
            blob_ules_laadimine_sisu(f"{book_id}.txt", response.text)
            return jsonify({"tulemus": "Raamatu loomine õnnestus", "raamatu_id": book_id}), 201
        except Exception:
            return jsonify({"error": "Raamat juba eksisteerib"}), 409
    return jsonify({"error": "Raamatut ei leitud Gutenbergis"}), 404

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0",port=80)
