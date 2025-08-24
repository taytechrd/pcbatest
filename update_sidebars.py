#!/usr/bin/env python3
"""
Sidebar güncelleme scripti
Tüm HTML sayfalarındaki sidebar menülerini dashboard ile aynı yapar
"""

import os
import re
import glob

# Dashboard'daki sidebar template'i
SIDEBAR_TEMPLATE = '''      <div class="sidebar-wrapper scrollbar scrollbar-inner">
        <div class="sidebar-content">
          <ul class="nav nav-secondary">
            <li class="nav-item">
              <a href="/">
                <i class="fas fa-home"></i>
                <p>Dashboard</p>
              </a>
            </li>
            <li class="nav-section">
              <span class="sidebar-mini-icon">
                <i class="fa fa-ellipsis-h"></i>
              </span>
              <h4 class="text-section">Test İşlemleri</h4>
            </li>
            <li class="nav-item">
              <a href="/test-execution">
                <i class="fas fa-play-circle"></i>
                <p>Test Çalıştır</p>
              </a>
            </li>
            <li class="nav-item">
              <a href="/test-monitoring">
                <i class="fas fa-desktop"></i>
                <p>Test İzleme</p>
              </a>
            </li>
            <li class="nav-item">
              <a href="/test-results">
                <i class="fas fa-chart-line"></i>
                <p>Test Sonuçları</p>
              </a>
            </li>
            <li class="nav-item">
              <a href="/scheduled-tests">
                <i class="fas fa-clock"></i>
                <p>Zamanlanmış Testler</p>
              </a>
            </li>
            <li class="nav-item">
              <a href="/communication-logs">
                <i class="fas fa-exchange-alt"></i>
                <p>Haberleşme Logları</p>
              </a>
            </li>
            <li class="nav-item">
              <a href="/reports">
                <i class="fas fa-file-alt"></i>
                <p>Raporlar</p>
              </a>
            </li>
            <li class="nav-section">
              <span class="sidebar-mini-icon">
                <i class="fa fa-ellipsis-h"></i>
              </span>
              <h4 class="text-section">Yönetim</h4>
            </li>
            {% if current_user.is_authenticated and current_user.role == 'admin' %}
            <li class="nav-item">
              <a data-bs-toggle="collapse" href="#userManagement">
                <i class="fas fa-users"></i>
                <p>Kullanıcı Yönetimi</p>
                <span class="caret"></span>
              </a>
              <div class="collapse show" id="userManagement">
                <ul class="nav nav-collapse">
                  <li>
                    <a href="/users">
                      <span class="sub-item">Kullanıcı Listesi</span>
                    </a>
                  </li>
                  <li>
                    <a href="/add-user">
                      <span class="sub-item">Yeni Kullanıcı</span>
                    </a>
                  </li>
                  <li>
                    <a href="/role-management">
                      <span class="sub-item">Rol Yönetimi</span>
                    </a>
                  </li>
                </ul>
              </div>
            </li>
            {% endif %}
            {% if current_user.is_authenticated and current_user.role == 'admin' %}
            <li class="nav-item">
              <a data-bs-toggle="collapse" href="#testManagement">
                <i class="fas fa-cogs"></i>
                <p>Test Yönetimi</p>
                <span class="caret"></span>
              </a>
              <div class="collapse" id="testManagement">
                <ul class="nav nav-collapse">
                  <li>
                    <a href="/test-types">
                      <span class="sub-item">Test Tipleri</span>
                    </a>
                  </li>
                  <li>
                    <a href="/test-scenarios">
                      <span class="sub-item">Test Senaryoları</span>
                    </a>
                  </li>
                  <li>
                    <a href="/pcba-models">
                      <span class="sub-item">PCBA Modelleri</span>
                    </a>
                  </li>
                </ul>
              </div>
            </li>
            {% endif %}
            <li class="nav-item">
              <a href="/connections">
                <i class="fas fa-plug"></i>
                <p>Bağlantı Yönetimi</p>
              </a>
            </li>
            <li class="nav-section">
              <span class="sidebar-mini-icon">
                <i class="fa fa-ellipsis-h"></i>
              </span>
              <h4 class="text-section">Ayarlar</h4>
            </li>
            <li class="nav-item">
              <a data-bs-toggle="collapse" href="#submenu">
                <i class="fas fa-cog"></i>
                <p>Settings</p>
                <span class="caret"></span>
              </a>
              <div class="collapse" id="submenu">
                <ul class="nav nav-collapse">
                  <li>
                    <a href="/user-settings">
                      <span class="sub-item">User Settings</span>
                    </a>
                  </li>
                  <li>
                    <a href="/system-settings">
                      <span class="sub-item">System Settings</span>
                    </a>
                  </li>
                  <li>
                    <a href="/test-parameters">
                      <span class="sub-item">Test Parameters</span>
                    </a>
                  </li>
                  <li>
                    <a href="/test-configuration">
                      <span class="sub-item">Test Configuration</span>
                    </a>
                  </li>
                </ul>
              </div>
            </li>
          </ul>
        </div>
      </div>'''

def update_sidebar_in_file(file_path):
    """Bir HTML dosyasındaki sidebar'ı günceller"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Sidebar wrapper'dan End Sidebar'a kadar olan kısmı bul
        pattern = r'<div class="sidebar-wrapper scrollbar scrollbar-inner">.*?</div>\s*</div>\s*<!-- End Sidebar -->'
        
        # Yeni sidebar ile değiştir
        new_content = re.sub(
            pattern, 
            SIDEBAR_TEMPLATE + '\n      </div>\n      <!-- End Sidebar -->',
            content, 
            flags=re.DOTALL
        )
        
        # Eğer değişiklik yapıldıysa dosyayı güncelle
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Güncellendi: {file_path}")
            return True
        else:
            print(f"⚠️  Sidebar bulunamadı: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Hata: {file_path} - {str(e)}")
        return False

def main():
    """Ana fonksiyon"""
    print("🔄 Sidebar güncelleme başlıyor...")
    
    # Dash klasöründeki tüm HTML dosyalarını bul
    html_files = glob.glob('dash/*.html')
    
    # Index.html'i hariç tut (zaten güncel)
    html_files = [f for f in html_files if not f.endswith('index.html')]
    
    updated_count = 0
    total_count = len(html_files)
    
    print(f"📁 {total_count} HTML dosyası bulundu")
    
    for file_path in html_files:
        if update_sidebar_in_file(file_path):
            updated_count += 1
    
    print(f"\n✨ Tamamlandı!")
    print(f"📊 {updated_count}/{total_count} dosya güncellendi")
    
    if updated_count > 0:
        print("\n🎯 Güncellenen özellikler:")
        print("  - Test İzleme menüsü eklendi")
        print("  - Zamanlanmış Testler menüsü eklendi") 
        print("  - Haberleşme Logları menüsü eklendi")
        print("  - Bağlantı Yönetimi menüsü eklendi")
        print("  - Test Parameters menüsü eklendi")
        print("  - Menü yapısı standardize edildi")

if __name__ == "__main__":
    main()