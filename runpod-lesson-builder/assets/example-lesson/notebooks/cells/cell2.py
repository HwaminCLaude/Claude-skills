print("CUDA 사용 가능:", torch.cuda.is_available())
print("GPU 이름:", torch.cuda.get_device_name(0))
print("GPU 전체 메모리(GB):", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1))