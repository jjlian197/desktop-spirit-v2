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
controls.enabled = false;
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
let mouthTarget = 0;
let lastMouthUpdateAt = 0;
let expression = 'neutral';
let bigHead = false;
let eyeTracking = true;
let lipSyncEnabled = true;
let baseHeadScale = null;
let genericRig = null;
let currentCharacterRoot = null;

const EXPRESSION_KEYWORDS = {
  happy: ['happy', 'smile', 'joy', 'laugh', 'grin'],
  angry: ['angry', 'anger', 'mad'],
  sad: ['sad', 'sorrow', 'tear', 'cry'],
  surprised: ['surprise', 'surprised', 'wide', 'wow'],
  sleepy: ['sleep', 'sleepy', 'blink', 'closed'],
  relaxed: ['relaxed', 'calm', 'soft', 'gentle'],
  mouthOpen: ['aa', 'ah', 'mouthopen', 'jawopen', 'openmouth', 'vrc.v_aa', 'm_a', 'm_opensmall', 'b_ah_r', 'b_ah_l'],
  mouthRound: ['m_o', 'oh', 'oo', 'ou', 'vrc.v_oh'],
};

function captureBaseTransform(node) {
  if (!node) return;
  if (!node.userData.sherryBaseRotation) {
    node.userData.sherryBaseRotation = node.rotation.clone();
  }
  if (!node.userData.sherryBaseScale) {
    node.userData.sherryBaseScale = node.scale.clone();
  }
}

function restoreBaseTransform(node) {
  if (!node) return;
  captureBaseTransform(node);
  node.rotation.copy(node.userData.sherryBaseRotation);
  node.scale.copy(node.userData.sherryBaseScale);
}

function nameMatches(name, patterns) {
  const lower = (name || '').toLowerCase();
  return patterns.some((pattern) => lower.includes(pattern));
}

function findFirstNode(rootObject, patterns, options = {}) {
  const predicate = options.predicate || (() => true);
  let found = null;
  rootObject.traverse((obj) => {
    if (found) return;
    if (!predicate(obj)) return;
    if (nameMatches(obj.name, patterns)) found = obj;
  });
  return found;
}

function findFirstBone(rootObject, patterns) {
  return findFirstNode(rootObject, patterns, { predicate: (obj) => obj.isBone });
}

function collectNodes(rootObject, predicate) {
  const result = [];
  rootObject.traverse((obj) => {
    if (predicate(obj)) result.push(obj);
  });
  return result;
}

function reparentHeadMeshes(rig) {
  if (!rig.faceDirection) return;
  if (rig.faceDirection.children && rig.faceDirection.children.length) return;

  const headMeshes = collectNodes(rig.root, (obj) => {
    if (!obj.isMesh) return false;
    const name = (obj.name || '').toLowerCase();
    return (
      name.includes('face') ||
      name.includes('eye') ||
      name.includes('hair') ||
      name.includes('bang')
    );
  });

  headMeshes.forEach((mesh) => {
    if (mesh !== rig.faceDirection && mesh.parent !== rig.faceDirection) {
      rig.faceDirection.attach(mesh);
    }
  });
}

function collectMorphIndices(mesh, patterns, excludePatterns = []) {
  const dict = mesh.morphTargetDictionary || {};
  return Object.entries(dict)
    .filter(([name]) => {
      if (!nameMatches(name, patterns)) return false;
      if (excludePatterns.length && nameMatches(name, excludePatterns)) return false;
      return true;
    })
    .map(([, index]) => index);
}

function buildGenericRig(rootObject) {
  const mouthShapeExcludes = ['m_', 'mouth', 'lip', 'aa', 'ah', 'oo', 'oh', 'm_a', 'm_o', 'laugh'];
  const rig = {
    root: rootObject,
    faceDirection: findFirstNode(rootObject, ['面部方向'], { predicate: (obj) => !obj.isMesh }),
    upperBodyMesh: findFirstNode(rootObject, ['up01'], { predicate: (obj) => obj.isMesh }),
    head: findFirstBone(rootObject, ['head', 'j_head', 'mixamorighead', '頭']),
    neck: findFirstBone(rootObject, ['neck', 'j_neck', 'mixamorigneck', '首']),
    chest: findFirstBone(rootObject, ['upperchest', 'chest', 'spine2', 'spine1', 'spine', '上半身', '胸']),
    jaw: findFirstBone(rootObject, ['jaw', 'mouth', '顎', 'あご']),
    leftEye: findFirstBone(rootObject, ['lefteye', 'eye_l', 'l_eye', '左目']),
    rightEye: findFirstBone(rootObject, ['righteye', 'eye_r', 'r_eye', '右目']),
    expressionTargets: [],
  };

  [rig.root, rig.faceDirection, rig.upperBodyMesh, rig.head, rig.neck, rig.chest, rig.jaw, rig.leftEye, rig.rightEye].forEach(captureBaseTransform);
  reparentHeadMeshes(rig);

  rootObject.traverse((obj) => {
    if (!obj.isMesh || !obj.morphTargetInfluences || !obj.morphTargetDictionary) return;
    const target = {
      mesh: obj,
      groups: {
        happy: collectMorphIndices(obj, EXPRESSION_KEYWORDS.happy, mouthShapeExcludes),
        angry: collectMorphIndices(obj, EXPRESSION_KEYWORDS.angry, mouthShapeExcludes),
        sad: collectMorphIndices(obj, EXPRESSION_KEYWORDS.sad, mouthShapeExcludes),
        surprised: collectMorphIndices(obj, EXPRESSION_KEYWORDS.surprised, mouthShapeExcludes),
        sleepy: collectMorphIndices(obj, EXPRESSION_KEYWORDS.sleepy, mouthShapeExcludes),
        relaxed: collectMorphIndices(obj, EXPRESSION_KEYWORDS.relaxed, mouthShapeExcludes),
        mouthOpen: collectMorphIndices(obj, EXPRESSION_KEYWORDS.mouthOpen),
        mouthRound: collectMorphIndices(obj, EXPRESSION_KEYWORDS.mouthRound),
        pupilUp: collectMorphIndices(obj, ['pupil_up']),
        pupilDown: collectMorphIndices(obj, ['pupil_down']),
        pupilLeft: collectMorphIndices(obj, ['pupil_l']),
        pupilRight: collectMorphIndices(obj, ['pupil_r']),
      },
    };

    const hasAnyGroup = Object.values(target.groups).some((indices) => indices.length);
    if (hasAnyGroup) {
      rig.expressionTargets.push(target);
    }
  });

  return rig;
}

function applyMorphGroup(groupName, value) {
  if (!genericRig) return;
  genericRig.expressionTargets.forEach((target) => {
    const indices = target.groups[groupName] || [];
    indices.forEach((index) => {
      target.mesh.morphTargetInfluences[index] = value;
    });
  });
}

function setMorphGroup(groupName, value) {
  if (!genericRig) return;
  genericRig.expressionTargets.forEach((target) => {
    const indices = target.groups[groupName] || [];
    indices.forEach((index) => {
      target.mesh.morphTargetInfluences[index] = value;
    });
  });
}

function resetMorphs() {
  if (!genericRig) return;
  genericRig.expressionTargets.forEach((target) => {
    Object.values(target.groups).forEach((indices) => {
      indices.forEach((index) => {
        target.mesh.morphTargetInfluences[index] = 0;
      });
    });
  });
}

function getFramingOptions() {
  if (bigHead) {
    return {
      targetHeight: 3.0,
      targetY: 0.84,
      cameraY: 0.9,
      lift: 0.04,
      padding: 0.92,
      visibleHeightRatio: 0.32,
    };
  }

  return {
    targetHeight: 2.05,
      targetY: 0.45,
    cameraY: 0.48,
    lift: 0.015,
    padding: 1.08,
    visibleHeightRatio: 1.0,
  };
}

function fitObjectToView(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  if (box.isEmpty()) return;

  const size = box.getSize(new THREE.Vector3());
  const options = getFramingOptions();
  const targetHeight = options.targetHeight;
  const scale = targetHeight / Math.max(size.y, 0.001);

  object3d.scale.setScalar(scale);
  object3d.rotation.y = Math.PI;
  object3d.position.set(0, 0, 0);

  const scaledBox = new THREE.Box3().setFromObject(object3d);
  const scaledCenter = scaledBox.getCenter(new THREE.Vector3());
  const scaledSize = scaledBox.getSize(new THREE.Vector3());

  object3d.position.x -= scaledCenter.x;
  object3d.position.z -= scaledCenter.z;
  object3d.position.y -= scaledBox.min.y;
  object3d.position.y -= scaledSize.y * options.lift;

  const framedBox = new THREE.Box3().setFromObject(object3d);
  const framedSize = framedBox.getSize(new THREE.Vector3());
  const framedCenter = framedBox.getCenter(new THREE.Vector3());

  const fovY = THREE.MathUtils.degToRad(camera.fov);
  const fovX = 2 * Math.atan(Math.tan(fovY / 2) * camera.aspect);
  const visibleHeight = framedSize.y * (options.visibleHeightRatio || 1.0);
  const distanceY = (visibleHeight * 0.5 * options.padding) / Math.tan(fovY / 2);
  const distanceX = (framedSize.x * 0.5 * options.padding) / Math.tan(fovX / 2);
  const distance = Math.max(distanceX, distanceY, framedSize.z * 1.4, 2.4);

  controls.target.set(0, framedSize.y * options.targetY, 0);
  camera.position.set(0, framedBox.min.y + framedSize.y * options.cameraY, distance);
  camera.near = 0.01;
  camera.far = Math.max(200, distance * 8);
  camera.updateProjectionMatrix();
}

function normalizeMaterials(rootObject) {
  let meshCount = 0;
  rootObject.traverse((obj) => {
    if (!obj.isMesh) return;
    meshCount += 1;
    obj.frustumCulled = false;
    obj.castShadow = false;
    obj.receiveShadow = false;

    const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
    materials.forEach((material) => {
      if (!material) return;
      const name = (material.name || '').toLowerCase();
      const isHairLike =
        name.includes('hair') ||
        name.includes('bang') ||
        name.includes('fx') ||
        name.includes('eye');
      const isBodyLike =
        name.includes('face') ||
        name.includes('up01') ||
        name.includes('down01') ||
        name.includes('item');

      material.side = THREE.DoubleSide;
      material.depthTest = true;
      material.depthWrite = true;
      material.premultipliedAlpha = false;

      if (isHairLike) {
        material.transparent = false;
        material.opacity = 1.0;
        material.alphaTest = Math.max(material.alphaTest || 0, 0.35);
      } else if (isBodyLike) {
        material.transparent = false;
        material.opacity = 1.0;
        material.alphaTest = 0.0;
        material.alphaMap = null;
      } else if (material.alphaMap) {
        material.transparent = true;
        material.alphaTest = Math.max(material.alphaTest || 0, 0.12);
      } else {
        material.transparent = false;
        material.alphaTest = 0.0;
      }

      material.needsUpdate = true;
    });
  });
  console.info('Normalized meshes:', meshCount);
}

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
  if (currentCharacterRoot) {
    fitObjectToView(currentCharacterRoot);
  }
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
  genericRig = null;
  currentCharacterRoot = null;
  mouthOpen = 0;
  mouthTarget = 0;
  lastMouthUpdateAt = 0;
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
  currentCharacterRoot = group;
  fitObjectToView(group);
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
  const effectiveMouthOpen = lipSyncEnabled ? mouthOpen : 0;

  if (currentVrm) {
    ['happy', 'angry', 'sad', 'relaxed', 'surprised', 'sleepy'].forEach((name) => {
      setVrmExpression(name, name === expression ? 1 : 0);
    });
    setVrmExpression('aa', effectiveMouthOpen);
  } else if (genericRig) {
    resetMorphs();
    const mappedExpression = expression === 'neutral' ? null : expression;
    if (mappedExpression) {
      applyMorphGroup(mappedExpression, 1);
    }
    applyMorphGroup('mouthOpen', effectiveMouthOpen * 0.78);
    applyMorphGroup('mouthRound', Math.max(0, effectiveMouthOpen - 0.28) * 0.22);
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
      mouth.scale.y = 1 + effectiveMouthOpen * 6;
      mouth.scale.x = 1 + effectiveMouthOpen * 0.45;
    }
  }
}

function applyLook() {
  const activeLook = eyeTracking ? look : { x: 0, y: 0 };
  const yaw = THREE.MathUtils.degToRad(activeLook.x * 18);
  const pitch = THREE.MathUtils.degToRad(-activeLook.y * 12);
  if (currentVrm && currentVrm.humanoid) {
    const head = currentVrm.humanoid.getNormalizedBoneNode('head');
    if (head) {
      head.rotation.y = 0;
      head.rotation.x = 0;
      if (!baseHeadScale) baseHeadScale = head.scale.clone();
      const scale = bigHead ? 1.18 : 1.0;
      head.scale.copy(baseHeadScale).multiplyScalar(scale);
    }
  } else if (genericRig) {
    [genericRig.root, genericRig.faceDirection, genericRig.upperBodyMesh, genericRig.head, genericRig.neck, genericRig.chest, genericRig.jaw, genericRig.leftEye, genericRig.rightEye].forEach(
      restoreBaseTransform,
    );

    if (genericRig.faceDirection) {
      genericRig.faceDirection.rotation.y += 0;
      genericRig.faceDirection.rotation.x += 0;
    } else if (genericRig.head) {
      genericRig.head.rotation.y += 0;
      genericRig.head.rotation.x += 0;
      if (bigHead) {
        genericRig.head.scale.multiplyScalar(1.18);
      }
    } else if (genericRig.neck) {
      genericRig.neck.rotation.y += 0;
      genericRig.neck.rotation.x += 0;
    }

    if (genericRig.leftEye) {
      genericRig.leftEye.rotation.y += yaw * 0.35;
      genericRig.leftEye.rotation.x += pitch * 0.35;
    }

    if (genericRig.rightEye) {
      genericRig.rightEye.rotation.y += yaw * 0.35;
      genericRig.rightEye.rotation.x += pitch * 0.35;
    }

    if (genericRig.jaw) {
      genericRig.jaw.rotation.x += effectiveMouthRotation();
    }

    const pupilScale = 0.55;
    setMorphGroup('pupilLeft', Math.max(0, look.x) * pupilScale);
    setMorphGroup('pupilRight', Math.max(0, -look.x) * pupilScale);
    setMorphGroup('pupilUp', Math.max(0, look.y) * pupilScale);
    setMorphGroup('pupilDown', Math.max(0, -look.y) * pupilScale);
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

function effectiveMouthRotation() {
  if (!lipSyncEnabled) return 0;
  return THREE.MathUtils.degToRad(mouthOpen * 16);
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
      normalizeMaterials(currentVrm.scene);
      currentCharacterRoot = currentVrm.scene;
      fitObjectToView(currentVrm.scene);
      scene.add(currentVrm.scene);
      genericRig = null;
    } else {
      normalizeMaterials(gltf.scene);
      currentCharacterRoot = gltf.scene;
      fitObjectToView(gltf.scene);
      scene.add(gltf.scene);
      fallback = gltf.scene;
      genericRig = buildGenericRig(gltf.scene);
      console.info('Generic rig detected:', {
        head: genericRig?.head?.name || null,
        jaw: genericRig?.jaw?.name || null,
        morphTargets: genericRig?.expressionTargets?.length || 0,
      });
    }
    mixer = gltf.animations.length ? new THREE.AnimationMixer(gltf.scene) : null;
    if (mixer) mixer.clipAction(gltf.animations[0]).play();
    console.info('Loaded model:', url);
  } catch (error) {
    console.error('Failed to load VRM/GLTF:', error);
    createFallback();
  }
}

function triggerMotion(group) {
  console.info('Ignoring motion request for generic Blender model:', group);
}

function setParameter(id, value) {
  if (id === 'ParamMouthOpenY' || id === 'ParamJawOpen') {
    mouthTarget = THREE.MathUtils.clamp(value, 0, 0.72);
    lastMouthUpdateAt = performance.now();
  }
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
  if (!lipSyncEnabled) {
    mouthTarget = 0;
  } else if (lastMouthUpdateAt && performance.now() - lastMouthUpdateAt > 140) {
    mouthTarget = 0;
  }
  const mouthBlend = mouthTarget > mouthOpen ? 0.42 : 0.24;
  mouthOpen = THREE.MathUtils.lerp(mouthOpen, mouthTarget, mouthBlend);
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
  lookAt(x, y) {
    look.x = THREE.MathUtils.clamp(x, -1, 1);
    look.y = THREE.MathUtils.clamp(y, -1, 1);
  },
  triggerMotion,
  resetPose,
  setBigHeadMode(enabled) {
    bigHead = !!enabled;
    if (currentCharacterRoot) {
      fitObjectToView(currentCharacterRoot);
    }
  },
  setLipSync(enabled) {
    lipSyncEnabled = !!enabled;
    if (!lipSyncEnabled) {
      mouthOpen = 0;
      mouthTarget = 0;
      lastMouthUpdateAt = 0;
    }
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
