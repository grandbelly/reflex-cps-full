/**
 * Node-RED 간단 설정 파일 (EcoAnP 프로젝트용)
 */

module.exports = {
    // 런타임 설정
    uiPort: process.env.PORT || 1880,
    
    // 플로우 파일 설정
    flowFile: 'flows.json',
    flowFilePretty: true,
    
    // 사용자 디렉토리 설정
    userDir: '/data/',
    
    // 보안 설정 비활성화 (개발용)
    adminAuth: false,
    
    // 로깅 설정
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },
    
    // 편집기 설정
    editorTheme: {
        projects: {
            enabled: false
        },
        palette: {
            editable: true
        },
        tours: false,
        header: {
            title: "EcoAnP Node-RED (간단 모드)"
        }
    },
    
    // 외부 모듈 설정
    externalModules: {
        autoInstall: false,
        palette: {
            allowInstall: true,
            allowUpdate: true,
            allowUpload: true
        }
    }
};

