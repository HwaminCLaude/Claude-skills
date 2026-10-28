x = torch.randn(4096, 4096, device="cuda")
y = x @ x
torch.cuda.synchronize()
print("이 노트북이 GPU에 만든 텐서(MB):", round(torch.cuda.memory_allocated() / 1024**2))
!nvidia-smi --query-gpu=memory.used,memory.total --format=csv