#!/usr/bin/env bash
# Создает удобный алиас для обновления Task Manager

ALIAS_NAME="tm-update"
ALIAS_COMMAND="sudo systemctl start task-manager-update"

echo "Добавляем алиас '$ALIAS_NAME' в ~/.bashrc..."

# Проверить что алиас еще не существует
if grep -q "alias $ALIAS_NAME=" ~/.bashrc 2>/dev/null; then
    echo "Алиас '$ALIAS_NAME' уже существует в ~/.bashrc"
else
    echo "" >> ~/.bashrc
    echo "# Task Manager update alias" >> ~/.bashrc
    echo "alias $ALIAS_NAME='$ALIAS_COMMAND'" >> ~/.bashrc
    echo "✅ Алиас добавлен в ~/.bashrc"
fi

echo ""
echo "Чтобы применить изменения, выполни:"
echo "  source ~/.bashrc"
echo ""
echo "Теперь для обновления просто набирай:"
echo "  $ALIAS_NAME"
