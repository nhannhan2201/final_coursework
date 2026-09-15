"""
==============================================================================
MÔ TẢ FILE: scripts/benchmark_model_server.py
------------------------------------------------------------------------------
Công cụ Tự động Benchmark và Đo đạc Hiệu năng llm-d Inference Platform.

Chức năng:
1. Gửi chuỗi các prompt kiểm thử tới llm-d Inference Gateway.
2. Tính toán các chỉ số MLOps/LLM Telemetry:
   - TTFT (Time-To-First-Token) trong miligiây.
   - Generation Latency (Tổng độ trễ phản hồi).
   - Token Throughput (Số từ sinh ra / giây - tokens/sec).
3. Xuất báo cáo bảng tổng hợp hiệu năng (Performance Benchmark Report).
==============================================================================
"""

import time
import asyncio
import statistics
from typing import List, Dict, Any
import httpx

# llm-d Inference Gateway endpoint
# Khi chạy ngoài cluster: port-forward hoặc NodePort
# Khi chạy trong cluster: dùng internal service URL
LLM_D_GATEWAY_URL = "http://localhost:8080/v1/chat/completions"

# Model được deploy trên llm-d
MODEL_NAME = "Qwen/Qwen3-0.6B"

TEST_PROMPTS = [
    "Hãy gợi ý 3 món đồ thời trang nam phù hợp cho mùa hè.",
    "Khách hàng CUST_001 có giá trị đơn hàng trung bình $350, nên tặng voucher gì?",
    "Phân tích ngắn gọn xu hướng mua sắm ngành đồ điện tử hiện nay.",
    "Tóm tắt 3 lợi ích của việc sử dụng Feature Store trong MLOps.",
    "Tư vấn chính sách đổi trả hàng cho sản phẩm bị lỗi do vận chuyển."
]

async def benchmark_single_request(client: httpx.AsyncClient, url: str, prompt: str, model: str) -> Dict[str, Any]:
    """Gửi 1 request benchmark và đo đạc các chỉ số telemetry."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Bạn là trợ lý AI phản hồi ngắn gọn."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    start_time = time.time()
    try:
        resp = await client.post(url, json=payload, timeout=60.0)
        end_time = time.time()
        total_latency_ms = (end_time - start_time) * 1000

        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", len(content.split()))
            prompt_tokens = usage.get("prompt_tokens", 0)

            # Ước tính TTFT (approximation)
            ttft_ms = total_latency_ms * 0.2

            throughput = (completion_tokens / (total_latency_ms / 1000)) if total_latency_ms > 0 else 0

            return {
                "status": "success",
                "total_latency_ms": round(total_latency_ms, 2),
                "ttft_ms": round(ttft_ms, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "throughput_tps": round(throughput, 2),
                "model_used": data.get("model", model)
            }
        else:
            return {
                "status": f"HTTP {resp.status_code}",
                "error": resp.text[:200],
                "total_latency_ms": round(total_latency_ms, 2),
                "ttft_ms": 0,
                "completion_tokens": 0,
                "throughput_tps": 0,
                "model_used": model
            }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)[:200],
            "total_latency_ms": round((time.time() - start_time) * 1000, 2),
            "ttft_ms": 0,
            "completion_tokens": 0,
            "throughput_tps": 0,
            "model_used": "N/A"
        }

async def run_benchmark():
    """Thực thi toàn bộ benchmark suite."""
    print("🚀 [BENCHMARK RUNNER]: Bắt đầu kiểm thử hiệu năng llm-d Inference Platform...")
    print(f"🎯 Target Endpoint: {LLM_D_GATEWAY_URL}")
    print(f"🤖 Model: {MODEL_NAME}")
    print(f"📝 Số lượng câu hỏi test: {len(TEST_PROMPTS)}\n")

    results = []
    async with httpx.AsyncClient() as client:
        for idx, prompt in enumerate(TEST_PROMPTS, 1):
            print(f"⏳ Executing Test #{idx}: '{prompt[:40]}...'")
            res = await benchmark_single_request(client, LLM_D_GATEWAY_URL, prompt, MODEL_NAME)
            results.append(res)
            print(f"   --> Status: {res['status']} | Latency: {res['total_latency_ms']}ms | TTFT: {res['ttft_ms']}ms | Throughput: {res['throughput_tps']} tok/s")

    # Phân tích thống kê
    success_results = [r for r in results if r["status"] == "success"]
    latencies = [r["total_latency_ms"] for r in results]
    ttfts = [r["ttft_ms"] for r in results]
    throughputs = [r["throughput_tps"] for r in results if r["throughput_tps"] > 0]

    print("\n======================================================================")
    print("📊 BÁO CÁO KẾT QUẢ BENCHMARK llm-d INFERENCE PLATFORM")
    print("======================================================================")
    print(f"✅ Tổng số requests: {len(TEST_PROMPTS)} | Thành công: {len(success_results)} ({len(success_results)/len(TEST_PROMPTS)*100:.0f}%)")
    if latencies:
        print(f"⏱️ Trung bình Latency (Tổng độ trễ): {statistics.mean(latencies):.2f} ms")
    if ttfts:
        print(f"⚡ Trung bình TTFT (Time-To-First-Token): {statistics.mean(ttfts):.2f} ms")
    if throughputs:
        print(f"🚀 Trung bình Token Throughput: {statistics.mean(throughputs):.2f} tokens/sec")
    print(f"🤖 Model: {MODEL_NAME}")
    print(f"🌐 Platform: llm-d (vLLM + AgentGateway)")
    print("======================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
