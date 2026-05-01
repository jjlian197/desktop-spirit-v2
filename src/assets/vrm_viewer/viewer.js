import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

const root = document.getElementById('app');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
camera.position.set(0, 1.35, 4.2);

const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setClearColor(0x000000, 0);
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
root.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.target.set(0, 1.2, 0);

scene.add(new THREE.AmbientLight(0xffffff, 1.35));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
keyLight.position.set(1.8, 3.0, 2.2);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0xb8e6ff, 0.9);
fillLight.position.set(-2.0, 1.2, 2.0);
scene.add(fillLight);

const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

let bridge = null;
let currentVrm = null;
let fallback = null;
let mixer = null;
let clock = new THREE.Clock();
let look = { x: 0, y: 0 };
let mouthOpen = 0;
let expression = 'neutral';
let bigHead = false;
let eyeTracking = true;
let baseHeadScale = null;

new QWebChannel(qt.webChannelTransport, (channel) => {
  bridge = channel.objects.vrmBridge;
  bridge.emitReady();
});

function resize() {
  const width = Math.max(1, root.clientWidth);
  const height = Math.max(1, root.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

window.addEventListener('resize', resize);
resize();

renderer.domElement.addEventListener('pointerdown', () => {
  if (bridge) bridge.emitTouched('tap', 'body');
});

function clearCharacter() {
  if (currentVrm) {
    scene.remove(currentVrm.scene);
    VRMUtils.deepDispose(currentVrm.scene);
    currentVrm = null;
  }
  if (fallback) {
    scene.remove(fallback);
    fallback.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
    });
    fallback = null;
  }
  mixer = null;
  baseHeadScale = null;
}

function makeMat(color, roughness = 0.72) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.02 });
}

function createFallback() {
  clearCharacter();
  const group = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.52, 1.25, 12, 24), makeMat(0xffffff));
  body.position.y = 0.68;
  group.add(body);

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.46, 32, 24), makeMat(0xfff4ec));
  head.name = 'FallbackHead';
  head.position.y = 1.62;
  group.add(head);

  const hair = new THREE.Mesh(new THREE.SphereGeometry(0.48, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.56), makeMat(0x25212a));
  hair.position.set(0, 1.72, 0.02);
  group.add(hair);

  const eyeMat = makeMat(0x2b2b34);
  const leftEye = new THREE.Mesh(new THREE.SphereGeometry(0.045, 16, 12), eyeMat);
  const rightEye = leftEye.clone();
  leftEye.position.set(-0.16, 1.64, 0.42);
  rightEye.position.set(0.16, 1.64, 0.42);
  group.add(leftEye, rightEye);

  const mouth = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.025, 0.018), makeMat(0xe35a80));
  mouth.name = 'FallbackMouth';
  mouth.position.set(0, 1.49, 0.44);
  group.add(mouth);

  const bow = new THREE.Mesh(new THREE.TorusKnotGeometry(0.12, 0.035, 64, 8), makeMat(0xe84b7f));
  bow.position.set(0, 0.25, 0.48);
  bow.rotation.set(1.1, 0.2, 0.0);
  group.add(bow);

  group.position.y = -0.55;
  scene.add(group);
  fallback = group;
}

function setVrmExpression(name, value) {
  if (!currentVrm || !currentVrm.expressionManager) return;
  const manager = currentVrm.expressionManager;
  if (manager.getExpressionTrackName && !manager.getExpressionTrackName(name)) return;
  try {
    manager.setValue(name, value);
  } catch (_) {
    // Some GLB files do not have VRM expression metadata.
  }
}

function applyExpression() {
  if (currentVrm) {
    ['happy', 'angry', 'sad', 'relaxed', 'surprised', 'sleepy'].forEach((name) => {
      setVrmExpression(name, name === expression ? 1 : 0);
    });
    setVrmExpression('aa', mouthOpen);
  }

  if (fallback) {
    const head = fallback.getObjectByName('FallbackHead');
    const mouth = fallback.getObjectByName('FallbackMouth');
    if (head) {
      const color = {
        happy: 0xffefe7,
        angry: 0xffd7d7,
        sad: 0xe8f1ff,
        relaxed: 0xffe2ec,
        surprised: 0xfff3d1,
        sleepy: 0xe7e2ff,
      }[expression] || 0xfff4ec;
      head.material.color.setHex(color);
    }
    if (mouth) {
      mouth.scale.y = 1 + mouthOpen * 6;
      mouth.scale.x = 1 + mouthOpen * 0.45;
    }
  }
}

function applyLook() {
  const yaw = THREE.MathUtils.degToRad(look.x * 18);
  const pitch = THREE.MathUtils.degToRad(-look.y * 12);
  if (currentVrm && currentVrm.humanoid) {
    const head = currentVrm.humanoid.getNormalizedBoneNode('head');
    if (head && eyeTracking) {
      head.rotation.y = yaw;
      head.rotation.x = pitch;
      if (!baseHeadScale) baseHeadScale = head.scale.clone();
      const scale = bigHead ? 1.18 : 1.0;
      head.scale.copy(baseHeadScale).multiplyScalar(scale);
    }
  }
  if (fallback) {
    fallback.rotation.y = yaw * 0.45;
    const head = fallback.getObjectByName('FallbackHead');
    if (head) {
      head.rotation.y = yaw;
      head.rotation.x = pitch;
      head.scale.setScalar(bigHead ? 1.18 : 1.0);
    }
  }
}

async function loadModel(url) {
  clearCharacter();
  try {
    const gltf = await loader.loadAsync(url);
    const vrm = gltf.userData.vrm;
    if (vrm) {
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.removeUnnecessaryJoints(gltf.scene);
      currentVrm = vrm;
      currentVrm.scene.rotation.y = Math.PI;
      currentVrm.scene.position.y = -0.95;
      scene.add(currentVrm.scene);
    } else {
      gltf.scene.position.y = -0.95;
      gltf.scene.scale.setScalar(1.2);
      scene.add(gltf.scene);
      fallback = gltf.scene;
    }
    mixer = gltf.animations.length ? new THREE.AnimationMixer(gltf.scene) : null;
    if (mixer) mixer.clipAction(gltf.animations[0]).play();
  } catch (error) {
    console.error('Failed to load VRM/GLTF:', error);
    createFallback();
  }
}

function triggerMotion(group) {
  if (group && group.toLowerCase().includes('tap')) {
    mouthOpen = Math.max(mouthOpen, 0.5);
  }
}

function setParameter(id, value) {
  if (id === 'ParamMouthOpenY' || id === 'ParamJawOpen') mouthOpen = THREE.MathUtils.clamp(value, 0, 1);
  if (id === 'ParamAngleX' || id === 'ParamBodyAngleX' || id === 'ParamEyeBallX') look.x = THREE.MathUtils.clamp(value / 30, -1, 1);
  if (id === 'ParamAngleY' || id === 'ParamBodyAngleY' || id === 'ParamEyeBallY') look.y = THREE.MathUtils.clamp(value / 30, -1, 1);
}

function resetPose() {
  look.x = 0;
  look.y = 0;
}

function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();
  if (mixer) mixer.update(delta);
  if (currentVrm) currentVrm.update(delta);
  mouthOpen = THREE.MathUtils.lerp(mouthOpen, 0, 0.08);
  applyExpression();
  applyLook();
  controls.update();
  renderer.render(scene, camera);
}

animate();

window.SherryVrm = {
  loadModel,
  loadFallback: createFallback,
  setExpression(name) {
    expression = name || 'neutral';
  },
  setParameter,
  triggerMotion,
  resetPose,
  setBigHeadMode(enabled) {
    bigHead = !!enabled;
  },
  setEyeTracking(enabled) {
    eyeTracking = !!enabled;
  },
  setBackground(color) {
    if (!color) {
      document.body.style.background = 'transparent';
      return;
    }
    document.body.style.background = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${(color[3] ?? 255) / 255})`;
  },
  setGradientBackground(color1, color2) {
    document.body.style.background = `linear-gradient(135deg, rgb(${color1.join(',')}), rgb(${color2.join(',')}))`;
  },
  setBackgroundImage(url) {
    document.body.style.background = `center / cover no-repeat url("${url}")`;
  },
  dispose() {
    clearCharacter();
    renderer.dispose();
  },
};
