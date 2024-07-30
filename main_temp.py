import struct
import subprocess

MARKERS = {
    b'\xFF\xD8': 'SOI',
    b'\xFF\xC0': 'SOF0',
    b'\xFF\xC2': 'SOF2',
    b'\xFF\xC4': 'DHT',
    b'\xFF\xDB': 'DQT',
    b'\xFF\xDA': 'SOS',
    b'\xFF\xD9': 'EOI',
    b'\xFF\xE0': 'APP0',
    b'\xFF\xE1': 'APP1',
    b'\xFF\xE2': 'APP2',
    b'\xFF\xE3': 'APP3',
    b'\xFF\xE4': 'APP4',
    b'\xFF\xE5': 'APP5',
    b'\xFF\xE6': 'APP6',
    b'\xFF\xE7': 'APP7',
    b'\xFF\xE8': 'APP8',
    b'\xFF\xE9': 'APP9',
    b'\xFF\xEA': 'APP10',
    b'\xFF\xEB': 'APP11',
    b'\xFF\xEC': 'APP12',
    b'\xFF\xED': 'APP13',
    b'\xFF\xEE': 'APP14',
    b'\xFF\xEF': 'APP15',
    b'\xFF\xFE': 'COM'
}


def parse_jpeg(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    index = 0
    d = {}
    while index < len(data):
        marker = data[index:index+2]
        if marker in MARKERS:
            marker_name = MARKERS[marker]
            print(f'Marker: {marker_name} (0x{marker.hex().upper()}) at offset {hex(index)}')
            index += 2
            if marker_name not in ['SOI', 'EOI']:
                length = struct.unpack('>H', data[index:index+2])[0]
                print(f'  Segment Length: {hex(length)} bytes')
                if marker_name in ['SOS']:
                    info = {"offset": index-2, "length": length - 1}
                else:
                    info = {"offset": index-2, "length": length + 2}
                if marker_name in d:
                    d[marker_name].append(info)
                else:
                    d[marker_name] = [info]
                index += length
            else:
                if marker_name == 'EOI':
                    break
        else:
            index += 1
    return d


def modify_file(in_path, out_path, d, new_app1_data, new_app2_data, video_file_path):
    with open(in_path, 'rb') as f_in:
        con = f_in.read()
    con = bytearray(con)
    con[d['APP1'][0]['offset'] + d['APP1'][0]['length'] : d['APP1'][0]['offset'] + d['APP1'][0]['length']] = new_app1_data[1] + new_app2_data
    del con[d['APP1'][0]['offset'] : d['APP1'][0]['offset'] + d['APP1'][0]['length']]
    con[d['APP0'][0]['offset'] + d['APP0'][0]['length'] : d['APP0'][0]['offset'] + d['APP0'][0]['length']] = new_app1_data[0]
    del con[d['APP0'][0]['offset'] : d['APP0'][0]['offset'] + d['APP0'][0]['length']]
    con = bytes(con)
    video_data = open(video_file_path, 'rb').read()
    print(f"video_data_length={len(video_data)}")
    with open(out_path, 'wb') as f_out:
        f_out.write(con + video_data)
    return len(video_data)


if __name__ == '__main__':
    in_path = r'2024_07_01_12_48_IMG_8474.JPG'
    in_vid_path = r'2024_07_01_12_48_IMG_8474.MOV'
    out_path = in_path + '.MP.JPG'

    video_file_path = r'output_video_1.mp4'

    command = [
        "ffmpeg",
        "-i", in_vid_path,
        "-vf", "scale=1080:1440",  # vertical support only for now
        "-c:v", "libx265",
        "-tag:v", "hvc1",
        "-crf", "28",
        "-preset", "medium",
        "-movflags", "+faststart",
        "-brand", "mp42",
        "-strict", "experimental",
        video_file_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    print("stdout:\n", result.stdout)
    print("stderr:\n", result.stderr)

    new_app1_data_2 = 'FFE1......0A'
    new_app1_data_2 = bytes.fromhex(new_app1_data_2)
    new_app1_data_1 = 'FFE1...............D9'
    new_app1_data_1 = bytes.fromhex(new_app1_data_1)
    new_app2_data = 'FFE2......FC'
    new_app2_data = bytes.fromhex(new_app2_data)
    new_app1_data = [new_app1_data_1, new_app1_data_2]
    d = parse_jpeg(in_path)
    print(d)

    video_data_len = modify_file(in_path, out_path, d, new_app1_data, new_app2_data, video_file_path)

    command = [
        "exiftool",
        "-XMP-GCamera:MicroVideoVersion=1",
        "-XMP-GCamera:MicroVideo=1",
        f"-XMP-GCamera:MicroVideoOffset={video_data_len}",
        f"-XMP-GCamera:MicroVideoPresentationTimestampUs={video_data_len // 2}",
        out_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    print("stdout:\n", result.stdout)
    print("stderr:\n", result.stderr)