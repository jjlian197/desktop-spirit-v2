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

scene.add(new THREE.AmbientLight(0xffffff, 0.95));
const hemiLight = new THREE.HemisphereLight(0xfff4ea, 0x8aa0c8, 0.78);
scene.add(hemiLight);

const keyLight = new THREE.DirectionalLight(0xffffff, 1.7);
keyLight.position.set(1.8, 3.0, 2.2);
scene.add(keyLight);
scene.add(keyLight.target);

const fillLight = new THREE.DirectionalLight(0xb8e6ff, 0.62);
fillLight.position.set(-2.0, 1.2, 2.0);
scene.add(fillLight);
scene.add(fillLight.target);

const faceLight = new THREE.DirectionalLight(0xfff2e8, 0.82);
scene.add(faceLight);
scene.add(faceLight.target);

const rimLight = new THREE.DirectionalLight(0xcfe1ff, 0.38);
rimLight.position.set(-1.4, 2.4, -1.8);
scene.add(rimLight);
scene.add(rimLight.target);

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
let gestureState = {
  wave: 0,
  shy: 0,
  talk: 0,
  waveSide: 'right',
  think: 0,
  stretch: 0,
  nod: 0,
  shake: 0,
};

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
    leftShoulder: findFirstBone(rootObject, ['leftshoulder', 'shoulder_l', 'l_shoulder', 'l clavicle', 'clavicle_l', '\u5de6\u80a9', '\u80a9.l', '\u80a9p.l', '\u80a9c.l']),
    rightShoulder: findFirstBone(rootObject, ['rightshoulder', 'shoulder_r', 'r_shoulder', 'r clavicle', 'clavicle_r', '\u53f3\u80a9', '\u80a9.r', '\u80a9p.r', '\u80a9c.r']),
    leftUpperArm: findFirstBone(rootObject, ['leftarm', 'upperarm_l', 'arm_l', 'l_arm', 'l upperarm', 'lupperarm', 'leftupperarm', '\u5de6\u8155', '\u8155.l']),
    rightUpperArm: findFirstBone(rootObject, ['rightarm', 'upperarm_r', 'arm_r', 'r_arm', 'r upperarm', 'rupperarm', 'rightupperarm', '\u53f3\u8155', '\u8155.r']),
    leftElbow: findFirstBone(rootObject, ['leftelbow', 'forearm_l', 'lowerarm_l', 'elbow_l', 'l_elbow', 'l forearm', 'lforearm', 'leftforearm', '\u5de6\u3072\u3058', '\u3072\u3058.l']),
    rightElbow: findFirstBone(rootObject, ['rightelbow', 'forearm_r', 'lowerarm_r', 'elbow_r', 'r_elbow', 'r forearm', 'rforearm', 'rightforearm', '\u53f3\u3072\u3058', '\u3072\u3058.r']),
    leftWrist: findFirstBone(rootObject, ['lefthand', 'hand_l', 'wrist_l', 'l_hand', 'l hand', 'lhand', 'lefthand', '\u5de6\u624b\u9996', '\u624b\u9996.l']),
    rightWrist: findFirstBone(rootObject, ['righthand', 'hand_r', 'wrist_r', 'r_hand', 'r hand', 'rhand', 'righthand', '\u53f3\u624b\u9996', '\u624b\u9996.r']),
    hips: findFirstBone(rootObject, ['hips', 'pelvis', 'Bip001Pelvis']),
    spine: findFirstBone(rootObject, ['spine', 'Bip001Spine']),
    leftUpperLeg: findFirstBone(rootObject, ['leftupperleg', 'upperleg_l', 'thigh_l', 'l_thigh', 'l_upperleg', '\u5de6\u5927\u817f']),
    rightUpperLeg: findFirstBone(rootObject, ['rightupperleg', 'upperleg_r', 'thigh_r', 'r_thigh', 'r_upperleg', '\u53f3\u5927\u817f']),
    leftLowerLeg: findFirstBone(rootObject, ['leftlowerleg', 'lowerleg_l', 'calf_l', 'l_calf', 'l_lowerleg', '\u5de6\u5c0f\u817f']),
    rightLowerLeg: findFirstBone(rootObject, ['rightlowerleg', 'lowerleg_r', 'calf_r', 'r_calf', 'r_lowerleg', '\u53f3\u5c0f\u817f']),
    expressionTargets: [],
  };

  rig.hasArmRig = Boolean(rig.leftUpperArm || rig.rightUpperArm || rig.leftShoulder || rig.rightShoulder);

  [
    rig.root,
    rig.faceDirection,
    rig.upperBodyMesh,
    rig.head,
    rig.neck,
    rig.chest,
    rig.jaw,
    rig.leftEye,
    rig.rightEye,
    rig.leftShoulder,
    rig.rightShoulder,
    rig.leftUpperArm,
    rig.rightUpperArm,
    rig.leftElbow,
    rig.rightElbow,
    rig.leftWrist,
    rig.rightWrist,
    rig.hips,
    rig.spine,
    rig.leftUpperLeg,
    rig.rightUpperLeg,
    rig.leftLowerLeg,
    rig.rightLowerLeg,
  ].forEach(captureBaseTransform);
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

function applyBoneRotation(node, rotation) {
  if (!node || !rotation) return;
  if (rotation.x) node.rotation.x += rotation.x;
  if (rotation.y) node.rotation.y += rotation.y;
  if (rotation.z) node.rotation.z += rotation.z;
}

function updateGestureState(delta) {
  gestureState.wave = Math.max(0, gestureState.wave - delta * 0.30);
  gestureState.shy = Math.max(0, gestureState.shy - delta * 0.22);
  gestureState.think = Math.max(0, gestureState.think - delta * 0.28);
  gestureState.stretch = Math.max(0, gestureState.stretch - delta * 0.18);
  gestureState.nod = Math.max(0, gestureState.nod - delta * 0.45);
  gestureState.shake = Math.max(0, gestureState.shake - delta * 0.35);

  const talkTarget = lipSyncEnabled && mouthOpen > 0.05 ? Math.min(0.55, mouthOpen * 0.9) : 0;
  gestureState.talk = THREE.MathUtils.lerp(gestureState.talk, talkTarget, 0.16);
}

function applyGenericArmGestures(rig, timeSeconds) {
  if (!rig?.hasArmRig) return;

  const wave = gestureState.wave;
  const shy = gestureState.shy;
  const talk = gestureState.talk;
  const talkSwing = Math.sin(timeSeconds * 6.8) * talk;
  const waveSwing = Math.sin(timeSeconds * 9.5) * wave;
  const rightBias = gestureState.waveSide === 'right' ? 1 : 0.35;
  const leftBias = gestureState.waveSide === 'left' ? 1 : 0.35;

  applyBoneRotation(rig.rightShoulder, {
    z: -0.15 * talk * rightBias - 0.22 * shy,
    x: -0.08 * talk * rightBias,
  });
  applyBoneRotation(rig.rightUpperArm, {
    z: -0.35 * talk * rightBias - 0.7 * wave * rightBias - 0.35 * shy,
    x: -0.18 * talk * rightBias - 0.5 * wave * rightBias,
    y: -0.08 * shy,
  });
  applyBoneRotation(rig.rightElbow, {
    z: -0.45 * talk * rightBias - 1.0 * wave * rightBias - 0.5 * shy,
    x: -0.12 * talk * rightBias - 0.3 * wave * rightBias,
  });
  applyBoneRotation(rig.rightWrist, {
    z: -0.15 * talk * rightBias + waveSwing * 0.4,
    x: talkSwing * 0.12 * rightBias,
  });

  applyBoneRotation(rig.leftShoulder, {
    z: 0.15 * talk * leftBias + 0.22 * shy,
    x: -0.06 * talk * leftBias,
  });
  applyBoneRotation(rig.leftUpperArm, {
    z: 0.3 * talk * leftBias + 0.4 * shy + 0.35 * wave * (gestureState.waveSide === 'left' ? 1 : 0),
    x: -0.15 * talk * leftBias - 0.15 * shy,
    y: 0.08 * shy,
  });
  applyBoneRotation(rig.leftElbow, {
    z: 0.35 * talk * leftBias + 0.6 * shy + 0.5 * wave * (gestureState.waveSide === 'left' ? 1 : 0),
    x: -0.1 * talk * leftBias,
  });
  applyBoneRotation(rig.leftWrist, {
    z: 0.12 * talk * leftBias + waveSwing * 0.25 * (gestureState.waveSide === 'left' ? 1 : 0),
    x: -talkSwing * 0.1 * leftBias,
  });
}

function applyIdleAnimation(rig, t) {
  if (!rig) return;

  // Breathing — subtle spine/chest oscillation
  const breathe = Math.sin(t * 1.8) * 0.008;
  if (rig.chest) {
    rig.chest.rotation.x += breathe;
  }
  if (rig.spine) {
    rig.spine.rotation.x += breathe * 0.4;
  }

  // Subtle body sway
  const sway = Math.sin(t * 0.7) * 0.012;
  const sway2 = Math.sin(t * 0.5 + 1.2) * 0.006;
  if (rig.hips) {
    rig.hips.rotation.y += sway;
    rig.hips.rotation.z += sway2;
  }
  if (rig.spine) {
    rig.spine.rotation.y += sway * 0.3;
  }

  // Weight shift
  const weightShift = Math.sin(t * 0.4) * 0.005;
  if (rig.hips) {
    rig.hips.rotation.z += weightShift;
  }
}

function applyThinkGesture(rig, t) {
  const think = gestureState.think;
  if (think <= 0 || !rig?.hasArmRig) return;
  const side = gestureState.waveSide === 'right' ? -1 : 1;

  applyBoneRotation(side < 0 ? rig.leftUpperArm : rig.rightUpperArm, {
    z: side * 0.45 * think,
    x: -0.35 * think,
  });
  applyBoneRotation(side < 0 ? rig.leftElbow : rig.rightElbow, {
    z: side * 0.6 * think,
    x: -0.25 * think,
  });
  applyBoneRotation(side < 0 ? rig.leftWrist : rig.rightWrist, {
    x: 0.15 * think,
    z: side * 0.1 * think,
  });
  if (rig.head) {
    rig.head.rotation.z += -side * 0.06 * think;
  }
}

function applyStretchGesture(rig, t) {
  const stretch = gestureState.stretch;
  if (stretch <= 0 || !rig) return;
  const up = Math.sin(t * 3.0) * 0.05 * stretch;
  applyBoneRotation(rig.leftUpperArm, { z: 0.6 * stretch, x: -0.3 * stretch + up });
  applyBoneRotation(rig.rightUpperArm, { z: -0.6 * stretch, x: -0.3 * stretch + up });
  applyBoneRotation(rig.leftElbow, { z: 0.2 * stretch });
  applyBoneRotation(rig.rightElbow, { z: -0.2 * stretch });
  if (rig.chest) {
    rig.chest.rotation.x -= 0.04 * stretch;
  }
}

function applyNodGesture(rig, t) {
  const nod = gestureState.nod;
  if (nod <= 0 || !rig?.head) return;
  rig.head.rotation.x += Math.abs(Math.sin(t * 8.0)) * 0.12 * nod;
}

function applyShakeGesture(rig, t) {
  const shake = gestureState.shake;
  if (shake <= 0 || !rig?.head) return;
  rig.head.rotation.y += Math.sin(t * 10.0) * 0.1 * shake;
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
  // VRM loader already handles coordinate orientation; only flip generic GLB models.
  if (!currentVrm) {
    object3d.rotation.y = Math.PI;
  }
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
  updateLightRig();
}

function diagnoseModel(rootObject, label) {
  const bones = [];
  const meshes = [];
  rootObject.traverse((obj) => {
    if (obj.isBone) bones.push(obj.name || '(unnamed)');
    if (obj.isMesh) {
      const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
      meshes.push({
        name: obj.name || '(unnamed)',
        visible: obj.visible,
        geometryVertexCount: obj.geometry?.attributes?.position?.count || 0,
        materials: mats.map((m) => {
          if (!m) return null;
          const texInfo = (tex) => {
            if (!tex) return null;
            const img = tex.image;
            return {
              w: img?.width || 0,
              h: img?.height || 0,
              format: tex.format,
              type: tex.type,
              colorSpace: tex.colorSpace,
              flipY: tex.flipY,
              hasData: !!(img && (img.data || img.src || img.complete !== false)),
            };
          };
          return {
            name: m.name,
            type: m.type,
            transparent: m.transparent,
            opacity: m.opacity,
            alphaTest: m.alphaTest,
            side: m.side,
            depthWrite: m.depthWrite,
            visible: m.visible,
            hasAlphaMap: !!m.alphaMap,
            map: texInfo(m.map),
          };
        }),
      });
    }
  });
  console.info(`[DIAG] === ${label} ===`);
  console.info(`[DIAG] Bones (${bones.length}):`, JSON.stringify(bones.slice(0, 30)));
  console.info(`[DIAG] Meshes (${meshes.length}):`);
  meshes.forEach((m) => {
    console.info(`[DIAG]   Mesh "${m.name}" visible=${m.visible} verts=${m.geometryVertexCount}`);
    m.materials.forEach((mat) => {
      if (mat) {
        const mapStr = mat.map
          ? `map=${mat.map.w}x${mat.map.h} cs=${mat.map.colorSpace} flipY=${mat.map.flipY} hasData=${mat.map.hasData}`
          : 'map=null';
        console.info(`[DIAG]     "${mat.name}" (${mat.type}): ${mapStr} side=${mat.side} transparent=${mat.transparent} opacity=${mat.opacity.toFixed(3)} alphaTest=${mat.alphaTest.toFixed(3)}`);
      }
    });
  });
  const box = new THREE.Box3().setFromObject(rootObject);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  console.info(`[DIAG] BBox: size=(${size.x.toFixed(3)}, ${size.y.toFixed(3)}, ${size.z.toFixed(3)}) center=(${center.x.toFixed(3)}, ${center.y.toFixed(3)}, ${center.z.toFixed(3)})`);
  console.info(`[DIAG] Root rotation: y=${THREE.MathUtils.radToDeg(rootObject.rotation.y).toFixed(1)}deg`);
}

function normalizeMaterials(rootObject) {
  const isVrm = !!currentVrm;
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

      // Always ensure double-side rendering and basic flags
      material.side = THREE.DoubleSide;
      material.depthTest = true;
      material.depthWrite = true;
      material.toneMapped = true;

      // For VRM models: be very conservative — only fix visibility issues,
      // don't override transparency/alphaTest that VRM loader already set up.
      if (isVrm) {
        // Flip textures: GLTF stores textures with flipY=false but Three.js WebGL
        // needs flipY=true for correct rendering (Y-axis is flipped in WebGL).
        [material.map, material.alphaMap, material.normalMap, material.roughnessMap, material.metalnessMap].forEach((tex) => {
          if (tex && tex.image && tex.flipY === false) {
            tex.flipY = true;
            tex.needsUpdate = true;
            console.info(`[DIAG] Flipped texture for "${obj.name}" (${tex.image?.width}x${tex.image?.height})`);
          }
        });

        // MeshBasicMaterial from VRM: ensure colorSpace and flipY are correct
        if (material.type === 'MeshBasicMaterial') {
          if (material.colorSpace) material.colorSpace = THREE.SRGBColorSpace;
          material.needsUpdate = true;
          return;
        }
        // MeshStandardMaterial without texture: visible grey fallback
        if (material.type === 'MeshStandardMaterial' && !material.map) {
          material.transparent = false;
          material.alphaTest = 0.0;
          material.opacity = 1.0;
          material.color.setHex(0xaaaaaa);
          material.needsUpdate = true;
          console.info(`[DIAG] Gave fallback grey color to "${obj.name}" (no texture)`);
        }
        material.needsUpdate = true;
        return;
      }

      // --- Generic (non-VRM) path: more aggressive normalization ---
      const name = (material.name || '').toLowerCase();
      const isHairLike =
        name.includes('hair') ||
        name.includes('bang') ||
        name.includes('fx');
      const isBodyLike =
        name.includes('face') ||
        name.includes('up01') ||
        name.includes('down01') ||
        name.includes('item');
      const isFaceLike = name.includes('face');

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

      if ('metalness' in material) {
        material.metalness = isFaceLike ? 0.0 : Math.min(material.metalness ?? 0.0, 0.05);
      }
      if ('roughness' in material) {
        material.roughness = isFaceLike ? 0.88 : Math.max(material.roughness ?? 0.72, 0.68);
      }
      if ('emissive' in material) {
        if (isFaceLike) {
          material.emissive.setRGB(0.08, 0.06, 0.06);
          material.emissiveIntensity = 0.18;
        } else {
          material.emissive.setRGB(0, 0, 0);
          material.emissiveIntensity = 0.0;
        }
      }

      material.needsUpdate = true;
    });
  });
  console.info('Normalized meshes:', meshCount, '(VRM:', isVrm, ')');
  diagnoseModel(rootObject, 'After normalizeMaterials');
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
  updateLightRig();
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
  gestureState.wave = 0;
  gestureState.shy = 0;
  gestureState.talk = 0;
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

function updateLightRig() {
  const target = controls.target.clone();
  keyLight.target.position.copy(target);
  fillLight.target.position.copy(target);
  faceLight.target.position.copy(target);
  rimLight.target.position.copy(target);

  const forward = new THREE.Vector3();
  camera.getWorldDirection(forward);

  faceLight.position.copy(camera.position).add(forward.clone().multiplyScalar(-0.35)).add(new THREE.Vector3(0, 0.2, 0.8));
  keyLight.position.set(camera.position.x + 1.8, camera.position.y + 1.8, camera.position.z + 1.6);
  fillLight.position.set(camera.position.x - 2.2, camera.position.y + 0.6, camera.position.z + 1.2);
  rimLight.position.set(camera.position.x - 1.2, camera.position.y + 1.4, camera.position.z - 2.0);
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
  const yaw = THREE.MathUtils.degToRad(activeLook.x * 10);
  const pitch = THREE.MathUtils.degToRad(-activeLook.y * 7);
  if (currentVrm && currentVrm.humanoid) {
    const head = currentVrm.humanoid.getNormalizedBoneNode('head');
    const neck = currentVrm.humanoid.getNormalizedBoneNode('neck');
    if (head) {
      head.rotation.y = yaw * 0.26;
      head.rotation.x = pitch * 0.2;
      if (!baseHeadScale) baseHeadScale = head.scale.clone();
      const scale = bigHead ? 1.18 : 1.0;
      head.scale.copy(baseHeadScale).multiplyScalar(scale);
    }
    if (neck) {
      neck.rotation.y = yaw * 0.1;
      neck.rotation.x = pitch * 0.08;
    }
  } else if (genericRig) {
    [genericRig.root, genericRig.faceDirection, genericRig.upperBodyMesh, genericRig.head, genericRig.neck, genericRig.chest, genericRig.jaw, genericRig.leftEye, genericRig.rightEye,
     genericRig.hips, genericRig.spine, genericRig.leftUpperLeg, genericRig.rightUpperLeg, genericRig.leftLowerLeg, genericRig.rightLowerLeg].forEach(
      restoreBaseTransform,
    );
    [genericRig.leftShoulder, genericRig.rightShoulder, genericRig.leftUpperArm, genericRig.rightUpperArm, genericRig.leftElbow, genericRig.rightElbow, genericRig.leftWrist, genericRig.rightWrist].forEach(
      restoreBaseTransform,
    );

    if (genericRig.faceDirection) {
      genericRig.faceDirection.rotation.y += yaw * 0.24;
      genericRig.faceDirection.rotation.x += pitch * 0.18;
      if (genericRig.upperBodyMesh) {
        genericRig.upperBodyMesh.rotation.y += yaw * 0.06;
        genericRig.upperBodyMesh.rotation.x += pitch * 0.04;
      }
    } else if (genericRig.head) {
      genericRig.head.rotation.y += yaw * 0.24;
      genericRig.head.rotation.x += pitch * 0.18;
      if (bigHead) {
        genericRig.head.scale.multiplyScalar(1.18);
      }
      if (genericRig.neck) {
        genericRig.neck.rotation.y += yaw * 0.1;
        genericRig.neck.rotation.x += pitch * 0.08;
      }
    } else if (genericRig.neck) {
      genericRig.neck.rotation.y += yaw * 0.12;
      genericRig.neck.rotation.x += pitch * 0.1;
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

    const now = performance.now() * 0.001;
    applyIdleAnimation(genericRig, now);
    applyGenericArmGestures(genericRig, now);
    applyThinkGesture(genericRig, now);
    applyStretchGesture(genericRig, now);
    applyNodGesture(genericRig, now);
    applyShakeGesture(genericRig, now);
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
      console.info('[DIAG] VRM detected. humanoid bones:',
        vrm.humanoid ? Object.keys(vrm.humanoid.humanBones).join(', ') : 'none');
      console.info('[DIAG] VRM expressions:',
        vrm.expressionManager ? Object.keys(vrm.expressionManager.expressions).join(', ') : 'none');
      diagnoseModel(currentVrm.scene, 'Before normalizeMaterials (VRM)');
      normalizeMaterials(currentVrm.scene);
      currentCharacterRoot = currentVrm.scene;
      fitObjectToView(currentVrm.scene);
      console.info('[DIAG] After fitObjectToView: rotation.y=', THREE.MathUtils.radToDeg(currentVrm.scene.rotation.y).toFixed(1), 'deg');
      scene.add(currentVrm.scene);
      genericRig = null;
    } else {
      console.warn('[DIAG] No VRM metadata found, treating as generic GLB');
      diagnoseModel(gltf.scene, 'Before normalizeMaterials (generic)');
      normalizeMaterials(gltf.scene);
      // Log all meshes to identify stage/ground objects
      gltf.scene.traverse((obj) => {
        if (obj.isMesh) {
          const box = new THREE.Box3().setFromObject(obj);
          const size = box.getSize(new THREE.Vector3());
          console.info(`[DIAG] Loaded mesh: "${obj.name}" verts=${obj.geometry?.attributes?.position?.count || 0} size=${size.x.toFixed(2)}x${size.y.toFixed(2)}x${size.z.toFixed(2)}`);
        }
      });
      // Remove stage/ground planes from the scene (by name pattern or flat geometry)
      const toRemove = [];
      gltf.scene.traverse((obj) => {
        if (!obj.isMesh) return;
        const n = (obj.name || '').toLowerCase();
        if (n.startsWith('plane') || n.includes('stage') || n.includes('ground')) {
          toRemove.push(obj);
          return;
        }
        // Detect flat ground plane by geometry (very thin in Y)
        const box = new THREE.Box3().setFromObject(obj);
        const size = box.getSize(new THREE.Vector3());
        const isFlat = size.y < 0.02 && size.x > 0.5 && size.z > 0.5;
        const isLargeArea = size.x * size.z > 4.0 && size.y < 0.1;
        if (isFlat || isLargeArea) {
          toRemove.push(obj);
        }
      });
      toRemove.forEach((obj) => {
        obj.parent?.remove(obj);
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) obj.material.dispose();
        console.info('[DIAG] Removed stage mesh:', obj.name);
      });
      currentCharacterRoot = gltf.scene;
      fitObjectToView(gltf.scene);
      scene.add(gltf.scene);
      fallback = gltf.scene;
      genericRig = buildGenericRig(gltf.scene);
      console.info('[DIAG] Generic rig bones:',
        'head=' + (genericRig?.head?.name || 'null'),
        'neck=' + (genericRig?.neck?.name || 'null'),
        'chest=' + (genericRig?.chest?.name || 'null'),
        'hips=' + (genericRig?.hips?.name || 'null'),
        'spine=' + (genericRig?.spine?.name || 'null'),
        'lShoulder=' + (genericRig?.leftShoulder?.name || 'null'),
        'rShoulder=' + (genericRig?.rightShoulder?.name || 'null'),
        'lUpperArm=' + (genericRig?.leftUpperArm?.name || 'null'),
        'rUpperArm=' + (genericRig?.rightUpperArm?.name || 'null'),
        'lElbow=' + (genericRig?.leftElbow?.name || 'null'),
        'rElbow=' + (genericRig?.rightElbow?.name || 'null'),
        'lWrist=' + (genericRig?.leftWrist?.name || 'null'),
        'rWrist=' + (genericRig?.rightWrist?.name || 'null'),
        'hasArmRig=' + (genericRig?.hasArmRig || false),
      );
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
  const name = (group || '').toLowerCase();
  if (name.includes('wave') || name.includes('tap') || name.includes('greet')) {
    gestureState.wave = 1.0;
    gestureState.waveSide = 'right';
    console.info('Triggered wave gesture');
    return;
  }
  if (name.includes('shy') || name.includes('love')) {
    gestureState.shy = 1.0;
    console.info('Triggered shy gesture');
    return;
  }
  if (name.includes('think') || name.includes('consider')) {
    gestureState.think = 1.0;
    gestureState.waveSide = Math.random() > 0.5 ? 'left' : 'right';
    console.info('Triggered think gesture');
    return;
  }
  if (name.includes('stretch') || name.includes('yawn')) {
    gestureState.stretch = 1.0;
    console.info('Triggered stretch gesture');
    return;
  }
  if (name.includes('nod') || name.includes('agree') || name.includes('yes')) {
    gestureState.nod = 1.0;
    console.info('Triggered nod gesture');
    return;
  }
  if (name.includes('shake') || name.includes('no') || name.includes('deny')) {
    gestureState.shake = 1.0;
    console.info('Triggered shake gesture');
    return;
  }
  // Idle — just reset all gesture states gently
  if (name.includes('idle') || name.includes('reset')) {
    gestureState.wave = 0;
    gestureState.shy = 0;
    gestureState.think = 0;
    gestureState.stretch = 0;
    gestureState.nod = 0;
    gestureState.shake = 0;
    console.info('Reset all gestures');
    return;
  }
  console.info('Unknown motion:', group);
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
  updateGestureState(delta);
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
