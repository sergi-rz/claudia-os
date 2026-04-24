let currentTask = null;
const queue = [];

export function enqueue(task) {
  return new Promise((resolve, reject) => {
    const item = { task, resolve, reject };
    if (!currentTask) {
      run(item);
    } else {
      queue.push(item);
    }
  });
}

async function run(item) {
  currentTask = item;
  try {
    const result = await item.task();
    item.resolve(result);
  } catch (err) {
    item.reject(err);
  } finally {
    currentTask = null;
    if (queue.length > 0) {
      run(queue.shift());
    }
  }
}

export function cancelCurrent() {
  if (currentTask && currentTask.childProcess) {
    currentTask.childProcess.kill('SIGTERM');
    return true;
  }
  return false;
}

export function setChildProcess(cp) {
  if (currentTask) {
    currentTask.childProcess = cp;
  }
}

export function getQueueLength() {
  return queue.length;
}

export function isBusy() {
  return currentTask !== null;
}
