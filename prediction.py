import requests, os, sys

# model_id = os.environ.get('NANONETS_MODEL_ID')
model_id = "b40c2427-0c1b-465b-a5f5-74a66dce8747"
# api_key = os.environ.get('NANONETS_API_KEY')
api_key = "13f5c022-e9c4-11ed-b37e-d24b52dfb1e9"
image_path = sys.argv[1]

url = 'https://app.nanonets.com/api/v2/ObjectDetection/Model/' + model_id + '/LabelFile/'

data = {'file': open(image_path, 'rb'),    'modelId': ('', model_id)}

response = requests.post(url, auth=requests.auth.HTTPBasicAuth(api_key, ''), files=data)

print(response.text)


# def fromImageToString(image_path):
#     model_id = os.environ.get('NANONETS_MODEL_ID')
#     api_key = os.environ.get('NANONETS_API_KEY')
#     image_path = sys.argv[1]
#
#     url = 'https://app.nanonets.com/api/v2/ObjectDetection/Model/' + model_id + '/LabelFile/'
#
#     data = {'file': open(image_path, 'rb'),    'modelId': ('', model_id)}
#
#     response = requests.post(url, auth=requests.auth.HTTPBasicAuth(api_key, ''), files=data)
#
#     return response