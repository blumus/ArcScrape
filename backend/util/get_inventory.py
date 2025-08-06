import boto3
from botocore.exceptions import ClientError

session = boto3.Session(region_name="us-east-1")
available = session.get_available_services()

results = {}

for service_name in available:
    if not service_name.startswith("s3"):
        continue
    try:
        client = session.client(service_name)
        functions = dir(client)
        # call all list/describe functions
        for fn in functions:
            if True:
                print(f"{service_name}: trying {fn}()")
                results[service_name] = getattr(client, fn)()
    except ClientError as e:
        results[service_name] = f"PermissionError: {e.response['Error']['Code']}"
    except Exception as e:
        results[service_name] = f"Error: {str(e)}"

# Optional: Save to JSON
import json
with open("aws_auto_resources.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print("✅ Done.")