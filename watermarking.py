import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

# Proses pembuatan WM
def create_binary_wm(size=32):
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    draw.text((2, 10), "ARA", fill=255) 
    return (np.array(img) > 127).astype(np.float32)

def create_random_wm(size=32):
    return np.random.default_rng(42).choice([-1.0, 1.0], size=(size, size)).astype(np.float32)

# Proses DCT
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
    orig = cv2.imread("foto.jpeg")
    if orig is None: print("foto.jpeg not found!"); return
    orig = cv2.resize(orig, (256, 256))
    alpha = 35.0
    
    wm_bin = create_binary_wm()
    wm_rnd = create_random_wm()

    img_wm_bin = embed_dct(orig, wm_bin, alpha)
    img_wm_rnd = embed_dct(orig, wm_rnd, alpha)
    cv2.imwrite("outputWatermarking/rawFile/watermarked_binary_ara.jpg", img_wm_bin)
    cv2.imwrite("outputWatermarking/rawFile/watermarked_random.jpg", img_wm_rnd)

    ext_bin = extract_dct(simulate_jpeg(img_wm_bin, 80), orig, alpha)
    ext_rnd = extract_dct(simulate_jpeg(img_wm_rnd, 80), orig, alpha)
    
    plt.imsave("outputWatermarking/rawFile/extracted_binary_visual.png", (ext_bin > 0.5), cmap='gray')
    plt.imsave("outputWatermarking/rawFile/extracted_random_visual.png", ext_rnd, cmap='gray')

    qf_test = [100, 70, 40, 10]
    
    for name, wm_o, wm_i in [("binary", wm_bin, img_wm_bin), ("random", wm_rnd, img_wm_rnd)]:
        fig, axes = plt.subplots(1, 4, figsize=(15, 4))
        fig.suptitle(f"Analisis Proses Dekomposisi Watermark {name.upper()} per Quality Factor")
        for i, q in enumerate(qf_test):
            decoded = simulate_jpeg(wm_i, q)
            ex = extract_dct(decoded, orig, alpha)
            disp = (ex > 0.5) if name == "binary" else ex
            axes[i].imshow(disp, cmap='gray')
            axes[i].set_title(f"QF {q}")
            axes[i].axis('off')
        plt.savefig(f"outputWatermarking/analysis/analysis_grid_{name}.png" if name=="binary" else f"outputWatermarking/analysis/analysis_grid_{name}.png")

    qfs = range(100, 5, -5)
    c_b, c_r = [], []
    for q in qfs:
        e_b = extract_dct(simulate_jpeg(img_wm_bin, q), orig, alpha)
        e_r = extract_dct(simulate_jpeg(img_wm_rnd, q), orig, alpha)
        c_b.append(np.corrcoef(wm_bin.flatten(), e_b.flatten())[0,1])
        c_r.append(np.corrcoef(wm_rnd.flatten(), e_r.flatten())[0,1])

    plt.figure(figsize=(10, 5))
    plt.plot(qfs, c_b, 'b-o', label='Binary ARA')
    plt.plot(qfs, c_r, 'r-s', label='Random Noise')
    plt.gca().invert_xaxis()
    plt.title("Perbandingan Robustness Watermark: Binary vs Random")
    plt.xlabel("JPEG Quality Factor"); plt.ylabel("Correlation Coefficient (r)")
    plt.legend(); plt.grid(True)
    plt.savefig("outputWatermarking/analysis/analysis_comparison_graph.png")

    print("SELESAI PROSES WATERMARMKING!")

if __name__ == "__main__":
    main()