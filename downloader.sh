#!/data/data/com.termux/files/usr/bin/bash

# YouTube Red Theme Colors
RED='\e[1;31m'
WHITE='\e[1;37m'
NC='\e[0m'

while true; do
    clear
    echo -e "${RED}"
    # Banner change karke "Master" kar diya hai
    toilet -f slant "Master"
    toilet -f slant "Downloader"
    echo -e "${WHITE}=========================================="
    echo -e "       UNIVERSAL DOWNLOADER | RED THEME   "
    echo -e "==========================================${NC}"
    
    echo -e "${RED}[1]${NC} Download Anything (YouTube/IG/FB/TikTok/etc)"
    echo -e "${RED}[2]${NC} Check Downloaded Files"
    echo -e "${RED}[3]${NC} Update Downloader"
    echo -e "${RED}[4]${NC} Exit"
    echo ""
    read -p "Select Option: " opt

    case $opt in
        1)
            read -p "Paste Any URL: " url
            echo -e "${RED}Fetching & Downloading...${NC}"
            yt-dlp -o '/sdcard/Download/%(title)s.%(ext)s' "$url"
            echo -e "${WHITE}Download Complete!${NC}"
            sleep 2
            ;;
        2)
            ls -1 /sdcard/Download/
            read -p "Press Enter to back..."
            ;;
        3)
            echo -e "${RED}Updating yt-dlp...${NC}"
            pip install -U yt-dlp
            sleep 2
            ;;
        4) exit ;;
    esac
done
