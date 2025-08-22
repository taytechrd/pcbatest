#!/usr/bin/env python3
"""
Test communication logs oluşturmak için script
"""

import sqlite3
from datetime import datetime, timedelta
import random
import json

def create_test_logs():
    # Veritabanına bağlan
    conn = sqlite3.connect('pcba_test.db')
    cursor = conn.cursor()
    
    # Örnek data setleri
    connection_types = ['serial', 'tcp']
    directions = ['sent', 'received']
    
    # Örnek komutlar ve yanıtlar
    sample_commands = [
        'AT+VERSION?',
        'AT+RESET',
        'AT+CONFIG=1,2,3',
        'GET /status HTTP/1.1',
        'POST /data HTTP/1.1',
        'PING 192.168.1.1',
        'READ_REGISTER 0x1001',
        'WRITE_REGISTER 0x1002,0xFF',
        'TEST_COMMAND',
        'CALIBRATE_SENSOR'
    ]
    
    sample_responses = [
        'OK',
        'ERROR: Invalid command',
        'Version: 1.2.3',
        'HTTP/1.1 200 OK',
        'HTTP/1.1 404 Not Found',
        'PONG',
        'Register value: 0x42',
        'Write successful',
        'Test completed',
        'Calibration done'
    ]
    
    # 50 test kaydı oluştur
    base_time = datetime.now() - timedelta(hours=2)
    
    for i in range(50):
        # Rastgele değerler
        connection_type = random.choice(connection_types)
        direction = random.choice(directions)
        is_error = random.choice([True, False, False, False])  # %25 hata oranı
        
        # Zaman damgası (son 2 saat içinde)
        timestamp = base_time + timedelta(minutes=random.randint(0, 120))
        
        # Data içeriği
        if direction == 'sent':
            data_ascii = random.choice(sample_commands)
        else:
            data_ascii = random.choice(sample_responses)
            
        data_hex = ' '.join([f'{ord(c):02X}' for c in data_ascii])
        data_size = len(data_ascii)
        
        # Bağlantı bilgileri
        if connection_type == 'serial':
            connection_id = f'COM{random.randint(1, 8)}'
        else:
            connection_id = f'192.168.1.{random.randint(100, 200)}:502'
            
        # Yanıt süresi
        response_time = random.uniform(10.0, 500.0) if not is_error else None
        
        # Metadata
        metadata = {
            'baud_rate': 9600 if connection_type == 'serial' else None,
            'timeout': 1000,
            'retry_count': random.randint(0, 3) if is_error else 0
        }
        
        # Veritabanına ekle
        cursor.execute('''
            INSERT INTO communication_logs (
                timestamp, connection_type, connection_id, direction,
                data_ascii, data_hex, data_size, is_error, response_time, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp.isoformat(),
            connection_type,
            connection_id,
            direction,
            data_ascii,
            data_hex,
            data_size,
            is_error,
            response_time,
            json.dumps(metadata)
        ))
    
    # Değişiklikleri kaydet
    conn.commit()
    conn.close()
    
    print(f"✅ 50 test communication log kaydı başarıyla oluşturuldu!")
    print(f"📊 Kayıtlar {base_time.strftime('%H:%M')} - {datetime.now().strftime('%H:%M')} arasına dağıtıldı")

if __name__ == '__main__':
    create_test_logs()