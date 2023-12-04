import re

def parse_m3u(file_path):
    channels = []

    with open(file_path, 'r') as file:
        lines = file.readlines()

    for line in lines:
        match = re.search(r'tvg-chno="(\d+)".*?,(.*?)$', line)
        if match:
            channel_number = match.group(1)
            channel_name = match.group(2)
            channels.append(f"{channel_number} - {channel_name}")

    return channels

def write_output(output_file, channels):
    with open(output_file, 'w') as file:
        file.write('\n'.join(channels))

if __name__ == "__main__":
    input_file = "lista_canales.m3u"
    output_file = "canales.txt"

    result_channels = parse_m3u(input_file)
    write_output(output_file, result_channels)

    print(f"Se ha creado el archivo {output_file} con la información de los canales.")

