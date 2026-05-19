import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import os

def create_binary_wm(size=32):
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    draw.text((2, 10), "ARA", fill=255) 
    return (np.array(img) > 127).astype(np.float32)

def embed_dct(img_bgr, wm, alpha=35.0):
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    Y = ycrcb[:, :, 0].astype(np.float32)
    wm_f = wm.flatten()
    idx = 0
    for r in range(0, Y.shape[0]-7, 8):
        for c in range(0, Y.shape[1]-7, 8):
            if idx < len(wm_f):
                block = cv2.dct(Y[r:r+8, c:c+8].copy())
                block[3, 3] += alpha * wm_f[idx]
                Y[r:r+8, c:c+8] = cv2.idct(block)
                idx += 1
    ycrcb[:, :, 0] = np.clip(Y, 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

def extract_dct(wm_img, orig_img, alpha=35.0):
    Y_wm = cv2.cvtColor(wm_img, cv2.COLOR_BGR2YCrCb)[:,:,0].astype(np.float32)
    Y_or = cv2.cvtColor(orig_img, cv2.COLOR_BGR2YCrCb)[:,:,0].astype(np.float32)
    res = []
    for r in range(0, Y_wm.shape[0]-7, 8):
        for c in range(0, Y_wm.shape[1]-7, 8):
            if len(res) < 1024:
                d_wm = cv2.dct(Y_wm[r:r+8, c:c+8].copy())
                d_or = cv2.dct(Y_or[r:r+8, c:c+8].copy())
                res.append((d_wm[3,3] - d_or[3,3]) / alpha)
    return np.array(res).reshape(32, 32)

def simulate_jpeg(img, q):
    buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), q])[1]
    return cv2.imdecode(buf, 1)

def main():
    paths = ["outputWatermarking/rawFile", "outputWatermarking/analysis", "outputWatermarking/process"]
    for p in paths: os.makedirs(p, exist_ok=True)

    orig = cv2.imread("foto.jpeg")
    if orig is None: print("foto.jpeg not found!"); return
    orig = cv2.resize(orig, (256, 256))
    alpha = 35.0
    
    grid_vis = orig.copy()
    for i in range(0, 256, 8):
        cv2.line(grid_vis, (i, 0), (i, 256), (255, 0, 0), 1)
        cv2.line(grid_vis, (0, i), (256, i), (255, 0, 0), 1)
    cv2.imwrite("outputWatermarking/process/step1_segmentation.png", grid_vis)

    ycrcb_vis = cv2.cvtColor(orig, cv2.COLOR_BGR2YCrCb)
    cv2.imwrite("outputWatermarking/process/step2_y_channel.png", ycrcb_vis[:,:,0])

    sample_block = ycrcb_vis[0:8, 0:8, 0].astype(np.float32)
    dct_vis = np.log(np.abs(cv2.dct(sample_block)) + 1)
    plt.imshow(dct_vis, cmap='viridis'); plt.axis('off')
    plt.savefig("outputWatermarking/process/step3_dct_visual.png"); plt.close()

    wm_bin = create_binary_wm()
    img_wm_bin = embed_dct(orig, wm_bin, alpha)
    
    diff = np.abs(img_wm_bin.astype(np.float32) - orig.astype(np.float32))
    diff_vis = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    cv2.imwrite("outputWatermarking/process/step4_embedding_residual.png", diff_vis)

    sample_y = cv2.cvtColor(img_wm_bin, cv2.COLOR_BGR2YCrCb)[:,:,0]
    cv2.imwrite("outputWatermarking/process/step5_idct_channel_y.png", sample_y)

    cv2.imwrite("outputWatermarking/process/step6_reconstruction_final.jpg", img_wm_bin)
    cv2.imwrite("outputWatermarking/rawFile/watermarked_ara.jpg", img_wm_bin)

    qf_test = [100, 70, 40, 10]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4))
    fig.suptitle("Analisis Dekomposisi Watermark ARA")
    
    qfs = range(100, 5, -5)
    correlations = []

    for i, q in enumerate(qf_test):
        decoded = simulate_jpeg(img_wm_bin, q)
        ex = extract_dct(decoded, orig, alpha)
        axes[i].imshow(ex > 0.5, cmap='gray')
        axes[i].set_title(f"QF {q}"); axes[i].axis('off')
    plt.savefig("outputWatermarking/analysis/analysis_grid_ara.png"); plt.close()

    for q in qfs:
        decoded = simulate_jpeg(img_wm_bin, q)
        ex = extract_dct(decoded, orig, alpha)
        correlations.append(np.corrcoef(wm_bin.flatten(), ex.flatten())[0,1])

    plt.figure(figsize=(10, 5))
    plt.plot(qfs, correlations, 'b-o', label='Watermark ARA')
    plt.gca().invert_xaxis()
    plt.title("Robustness Analysis: ARA Watermark")
    plt.xlabel("JPEG Quality Factor"); plt.ylabel("Correlation Coefficient (r)")
    plt.legend(); plt.grid(True)
    plt.savefig("outputWatermarking/analysis/analysis_graph_ara.png"); plt.close()
    
    ext_final = extract_dct(img_wm_bin, orig, alpha)
    plt.imsave("outputWatermarking/rawFile/extracted_binary_visual.png", (ext_final > 0.5), cmap='gray')

    print("\nPROSES SELESAI!")
    print("Semua file tersimpan di folder 'outputWatermarking'.")

if __name__ == "__main__":
    main()