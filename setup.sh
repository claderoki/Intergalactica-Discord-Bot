eval "$(ssh-agent -s)"
ssh-add ~/.ssh/git
# git pull && python3.8 -m src --mode=production