/**
 * Node-RED 설정 파일 (EcoAnP 프로젝트용)
 * 라즈베리파이 최적화 설정
 */

module.exports = {
    // 런타임 설정
    uiPort: process.env.PORT || 1880,
    mqttReconnectTime: 15000,
    serialReconnectTime: 15000,
    debugMaxLength: 1000,
    
    // 플로우 파일 설정
    flowFile: 'flows.json',
    flowFilePretty: true,
    
    // 사용자 디렉토리 설정
    userDir: '/data/',
    
    // 보안 설정 (프로덕션에서는 변경 필요)
    adminAuth: {
        type: "credentials",
        users: [{
            username: "admin",
            password: "$2b$08$zZWtXTja0fB1pzD4sHCMyOCMYz2Z6dNbM6tl8sJogENOMcxWV9DN.", // "password"
            permissions: "*"
        }]
    },
    
    // HTTPS 설정 (필요시)
    // https: {
    //     key: require("fs").readFileSync('privatekey.pem'),
    //     cert: require("fs").readFileSync('certificate.pem')
    // },
    
    // 함수 설정
    functionGlobalContext: {
        // 글로벌 변수 설정
        moment: require('moment'),
        // 추가 라이브러리는 여기에
    },
    
    // 로깅 설정
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        },
        file: {
            level: "info",
            filename: "/data/node-red.log",
            maxFiles: 5,
            maxSize: "10MB"
        }
    },
    
    // 편집기 설정
    editorTheme: {
        projects: {
            enabled: true
        },
        palette: {
            editable: true
        },
        tours: false,
        header: {
            title: "EcoAnP Node-RED",
            image: "/absolute/path/to/your/node-red-icon.png"
        }
    },
    
    // 컨텍스트 스토리지
    contextStorage: {
        default: {
            module: "localfilesystem"
        },
        memoryOnly: {
            module: "memory"
        }
    },
    
    // 외부 모듈 설정
    externalModules: {
        autoInstall: false,
        autoInstallRetry: 30,
        palette: {
            allowInstall: true,
            allowUpdate: true,
            allowUpload: true
        }
    },
    
    // 라즈베리파이 최적화
    runtimeState: {
        enabled: false,
        ui: false
    }
};

