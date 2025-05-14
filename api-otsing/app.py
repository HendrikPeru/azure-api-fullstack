from flask import Flask, request, jsonify
from azure.storage.blob import BlobServiceClient
import os
import json
from flask_cors import CORS


app = Flask(__name__)
cors = CORS(app, resources={r"/raamatud/*": {"origins": "*"}, r"/raamatu_otsing/*": {"origins": "*"}})


blob_connection_string = os.getenv('AZURE_BLOB_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
blob_container_name = "peru"

def blob_raamatute_nimekiri():
    container_client = blob_service_client.get_container_client(container=blob_container_name)
    return [blob.name for blob in container_client.list_blobs() if blob.name.endswith(".txt")]

def blob_alla_laadimine(faili_nimi):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    return blob_client.download_blob().content_as_text()

@app.route('/raamatu_otsing/<book_id>', methods=['POST'])
def otsi_sonaraamatust(book_id):
    if not book_id.isnumeric():
        return jsonify({"error": "Vigane raamatu ID"}), 400

    input_data = json.loads(request.data)
    sone = input_data.get("sone")
    if not sone:
        return jsonify({"error": "Puuduv sõne"}), 400

    try:
        tekst = blob_alla_laadimine(f"{book_id}.txt")
    except Exception:
        return jsonify({"error": "Raamatut ei leitud"}), 404

    leitud = 0
    for rida in tekst.splitlines():
        leitud += rida.lower().split().count(sone.lower())

    return jsonify({"raamatu_id": book_id, "sone": sone, "leitud": leitud}), 200


@app.route('/raamatu_otsing/', methods=['POST', 'OPTIONS'])
def otsi_koikidest_raamatutest():
    if request.method == 'OPTIONS':
        return '', 204

    input_data = json.loads(request.data)
    sone = input_data.get("sone", "")

    tulemused = []
    for blob_nimi in blob_raamatute_nimekiri():
        try:
            tekst = blob_alla_laadimine(blob_nimi)
            leitud = sum([rida.lower().split().count(sone.lower()) for rida in tekst.splitlines()])
            if leitud > 0:
                tulemused.append({
                    "raamatu_id": int(blob_nimi.split(".")[0]),
                    "leitud": leitud
                })
        except:
            continue

    return jsonify({"sone": sone, "tulemused": tulemused})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
