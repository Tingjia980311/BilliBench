import dask.dataframe as dd
import os
import tempfile
from google.cloud import storage

# Fetch required environment variables
BENCH_HOME = os.getenv("BENCH_HOME")
project_id = os.getenv("GCP_PROJECT")
bucket_name = os.getenv("GCP_BUCKET")

if not BENCH_HOME or not project_id or not bucket_name:
    raise EnvironmentError("Required environment variables (BENCH_HOME, GCP_PROJECT, GCP_BUCKET) are not set.")

def initialize_storage(project_id, bucket_name):
    """Initialize Google Cloud Storage client and bucket."""
    storage_client = storage.Client(project=project_id)
    return storage_client.get_bucket(bucket_name)

blocksize_dict = {
    "small": "250MB",
    "medium": "125MB",
    "large": "12MB",
}

def handler(events):
    """
    Args: events (dict) including 'size' parameter.
    Returns: int 0 on success, raises exception on failure.
    """
    try:
        # Initialize Google Cloud Storage
        bucket = initialize_storage(project_id, bucket_name)

        # Temporary directory for processing
        with tempfile.TemporaryDirectory(dir=BENCH_HOME) as tmp_dir:
            # define the paths
            x1_path = os.path.join(tmp_dir, f"{events['size']}_join1.csv")
            x2_path = os.path.join(tmp_dir, f"{events['size']}_join2.csv")
            output_path = os.path.join(tmp_dir, f"{events['size']}_join_result.csv")

            # download the dataset from GCP bucket
            blob = bucket.blob(f"Func19_join/{events['size']}_join1.csv")
            blob.chunk_size = 1<<30
            blob.download_to_filename(x1_path)
            blob = bucket.blob(f"Func19_join/{events['size']}_join2.csv")
            blob.chunk_size = 1<<30
            blob.download_to_filename(x2_path)
            
            # load the dataset
            x1 = dd.read_csv(x1_path, blocksize=blocksize_dict[events["size"]])
            x2 = dd.read_csv(x2_path, blocksize=blocksize_dict[events["size"]])
            
            # perform the join
            ans = x1.merge(x2, on='id0').compute()
            ans.reset_index(inplace=True)

            # save the result
            ans.to_csv(output_path, index=False)

            # upload the result to GCP bucket
            blob = bucket.blob(f"Func19_join/{events['size']}_join_result.csv")
            blob.chunk_size = 1<<30
            blob.upload_from_filename(output_path)

            return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    try:
        ret = handler({"size": "small"})
        print(f"Result: {ret}")
    except Exception as e:
        print(f"Error: {e}")
