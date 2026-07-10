#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streaming Patch Script - new_result.html'e streaming desteği ekler
CHUNKED WRITE PROTOCOL uyumlu surgical edit
"""
import sys

def apply_streaming_patch():
    """new_result.html'de AI çağrısını streaming'e çevir"""

    template_path = "templates/new_result.html"

    print(f"[PATCH] {template_path} okunuyor...")
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Eski fetch() kodunu bul
    old_code_marker = 'fetch( "/api/get_ai_interpretation", {'

    if old_code_marker not in content:
        print("[ERROR] Eski kod bulunamadı! fetch() çağrısı zaten değiştirilmiş olabilir.")
        return False

    # Yeni streaming kodu
    new_streaming_code = '''// ⚡ STREAMING DESTEĞI - SSE ile gerçek zamanlı AI yorumu
      console.log( "[ORBIS] 🚀 Streaming AI yorumu başlatılıyor..." );

      // Streaming indicator ekle
      $body.html( `
        <div class="flex items-center gap-3 mb-4 p-3 bg-white/5 rounded-lg">
          <div class="w-4 h-4 border-2 border-green-500/30 border-t-green-500 rounded-full animate-spin"></div>
          <span class="text-[11px] text-slate-300">AI yanıt yazıyor...</span>
        </div>
        <div id="streaming-content" class="text-[11px] leading-relaxed"></div>
      `);

      var streamingContent = '';
      var startTime = Date.now();

      fetch( "/api/ai/interpret-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify( {
          natal_data: astroData,
          interpretation_type: tabId,
          user_name: astroData.user_name || "Kullanıcı",
          device_id: deviceId,
          email: userEmail
        } )
      } )
        .then( async function ( response ) {
          // Günlük limit kontrolü
          if ( response.status === 429 ) {
            $body.html( `
              <div class="flex flex-col items-center justify-center py-8 px-4 text-center">
                <div class="w-20 h-20 rounded-full bg-amber-500/20 flex items-center justify-center mb-6">
                  <span class="material-icons-round text-4xl text-amber-400">videocam</span>
                </div>
                <h3 class="text-white font-bold text-lg mb-3">Reklam İzleme Gerekli</h3>
                <p class="text-slate-400 text-sm mb-6 max-w-xs">
                  AI yorum almak icin lutfen kisa bir reklam izleyin.
                  Uygulamamiz tamamen ucretsizdir.
                </p>
                <button onclick="closeAIModal()" class="px-6 py-3 bg-slate-700 text-white font-bold rounded-xl active:scale-95 transition-all">
                  Tamam
                </button>
              </div>
            `);
            return;
          }

          if ( !response.ok ) {
            throw new Error( `HTTP ${response.status}` );
          }

          // SSE Stream'i oku
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let chunkCount = 0;
          let firstChunkTime = null;

          while ( true ) {
            const { done, value } = await reader.read();
            if ( done ) break;

            buffer += decoder.decode( value, { stream: true } );
            const lines = buffer.split( '\\n' );
            buffer = lines.pop();

            for ( const line of lines ) {
              if ( !line.startsWith( 'data: ' ) ) continue;

              try {
                const data = JSON.parse( line.slice( 6 ) );

                if ( data.type === 'chunk' ) {
                  chunkCount++;
                  if ( firstChunkTime === null ) {
                    firstChunkTime = Date.now() - startTime;
                    console.log( `[ORBIS] ⚡ İlk chunk ${firstChunkTime}ms'de geldi` );
                    $body.find( '.animate-spin' ).parent().remove();
                  }

                  streamingContent += data.content;
                  $( '#streaming-content' ).html( marked.parse( streamingContent ) );

                  const $modalBody = $( '.ai-modal-body' );
                  if ( $modalBody.length ) {
                    $modalBody.scrollTop( $modalBody[0].scrollHeight );
                  }

                } else if ( data.type === 'done' ) {
                  const totalTime = Date.now() - startTime;
                  console.log( `[ORBIS] ✅ Streaming tamamlandı (${chunkCount} chunks, ${totalTime}ms)` );
                  console.log( `[ORBIS] ⚡ İlk chunk: ${firstChunkTime}ms | Toplam: ${totalTime}ms` );

                  currentInterpretationText = streamingContent;
                  $( '#ai-modal-footer' ).removeClass( 'hidden' );

                } else if ( data.type === 'error' ) {
                  throw new Error( data.message );
                }

              } catch ( parseError ) {
                console.warn( "[ORBIS] ⚠️ SSE parse error:", parseError );
              }
            }
          }

          if ( streamingContent ) {
            currentInterpretationText = streamingContent;
            $( '#streaming-content' ).html( marked.parse( streamingContent ) );
            $( '#ai-modal-footer' ).removeClass( 'hidden' );
          }
        } )
        .catch( function ( error ) {
          console.error( "[ORBIS] ❌ Streaming error:", error );
          $body.html( `
            <div class="text-center py-8">
              <p class="text-red-400 text-xs mb-2">⚠️ Bağlantı Hatası</p>
              <p class="text-slate-400 text-[10px]">${error.message || 'Bilinmeyen hata'}</p>
            </div>
          `);
        } );'''

    # Eski kodu bul ve değiştir (satır numarası yerine pattern matching)
    # fetch() başlangıcından .catch() bitişine kadar
    import re

    # Pattern: fetch( "/api/get_ai_interpretation", { ... } ).then(...).catch(...);
    pattern = r'fetch\( "/api/get_ai_interpretation",[\s\S]*?\}\s*\)\s*\.catch\([^)]*\)\s*;'

    matches = list(re.finditer(pattern, content))

    if not matches:
        print("[ERROR] Regex pattern ile eski kod bulunamadı!")
        return False

    if len(matches) > 1:
        print(f"[WARNING] {len(matches)} eşleşme bulundu, ilki kullanılacak")

    match = matches[0]
    old_code = match.group(0)

    print(f"[PATCH] Eski kod bulundu: {len(old_code)} karakter")
    print(f"[PATCH] Konum: {match.start()} - {match.end()}")

    # Yeni kod ile değiştir
    new_content = content[:match.start()] + new_streaming_code + content[match.end():]

    # Backup oluştur
    backup_path = template_path + ".backup"
    print(f"[PATCH] Backup oluşturuluyor: {backup_path}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Yeni içeriği yaz
    print(f"[PATCH] Yeni içerik yazılıyor...")
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("[SUCCESS] ✅ Streaming patch başarıyla uygulandı!")
    print(f"[INFO] Backup: {backup_path}")
    print(f"[INFO] Eski kod boyutu: {len(old_code)} karakter")
    print(f"[INFO] Yeni kod boyutu: {len(new_streaming_code)} karakter")

    return True

if __name__ == "__main__":
    try:
        success = apply_streaming_patch()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] Patch başarısız: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
