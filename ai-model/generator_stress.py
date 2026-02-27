import boto3, json, random, time
kinesis = boto3.client('kinesis', region_name='ap-northeast-2')
print("🚀 Stress test: 2000 records to paysim-stream")
start = time.time()
for i in range(2000):
    record = {
        "step": i, 
        "amount": random.uniform(100, 200000),
        "nameOrig": f"user_{i}",
        "type": random.choice(["TRANSFER", "PAYMENT"])
    }
    kinesis.put_record(
        StreamName='paysim-stream', 
        Data=json.dumps(record), 
        PartitionKey=str(i % 1)  # 단일 shard
    )
    if i % 500 == 0: print(f"Sent {i}/2000")
print(f"✅ Completed in {time.time()-start:.1f}s")
