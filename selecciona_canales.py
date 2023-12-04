import re

def parse_m3u(file_path):
    channels = []

    with open(file_path, 'r') as file:
        lines = file.readlines()

    for i in range(len(lines)-1):
        # Busca la información del canal en las líneas que contienen tvg-chno
        match_tvg_chno = re.search(r'tvg-chno="(\d+)".*?,(.*?)$', lines[i])
        if match_tvg_chno:
            channel_number = match_tvg_chno.group(1)
            channel_name = match_tvg_chno.group(2)

            # Busca la dirección web en la siguiente línea que contiene la palabra "stream"
            match_url = re.search(r'^(.*?stream[^\s]+)', lines[i+1])
            if match_url:
                channel_url = match_url.group(1)
                channels.append(f"{channel_number} - {channel_name} - {channel_url}")

    return channels

def write_output(output_file, channels):
    with open(output_file, 'w') as file:
        file.write('\n'.join(channels))

if __name__ == "__main__":
    input_file = "channel_list.m3u"
    output_file = "channels.txt"

    result_channels = parse_m3u(input_file)
    write_output(output_file, result_channels)

    print(f"Se ha creado el archivo {output_file} con la información de los canales.")


